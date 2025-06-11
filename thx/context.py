# Copyright 2022 Amethyst Reese
# Licensed under the MIT License

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
from itertools import chain
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Sequence, Tuple

import tomli

from aioitertools.asyncio import as_generated

from .runner import check_command
from .types import (
    CommandError,
    Config,
    Context,
    Event,
    Options,
    StrPath,
    VenvCreate,
    VenvError,
    VenvReady,
    Version,
)
from .utils import timed, venv_bin_path, version_match, which

LOG = logging.getLogger(__name__)
PYTHON_VERSION_RE = re.compile(r"Python (\d+\.\d+[a-zA-Z0-9-_.]+)\+?")
PYTHON_VERSIONS: Dict[Path, Optional[Version]] = {}
TIMESTAMP = "thx.timestamp"
PYPROJECT_HASH = "thx.pyproject.hash"
PROJECT_REBUILD_KEYS = [
    "build-system",
    "project",
    "tool.thx.requirements",
    "tool.thx.extras",
]


def venv_path(config: Config, version: Version) -> Path:
    return config.root / ".thx" / "venv" / str(version)


def runtime_version(binary: Path) -> Optional[Version]:
    if binary not in PYTHON_VERSIONS:
        try:
            proc = subprocess.run(
                (binary.as_posix(), "-V"),
                capture_output=True,
                encoding="utf-8",
                timeout=1,
            )

        except Exception as e:
            LOG.warning("running `%s -V` failed: %s", binary, e)
            PYTHON_VERSIONS[binary] = None
            return None

        match = PYTHON_VERSION_RE.search(proc.stdout)
        if not match:
            LOG.warning(
                "running `%s -V` gave unexpected version string: %r",
                binary,
                proc.stdout,
            )
            if proc.stderr:
                LOG.warning(
                    "unexpected version string included stderr:\n%s", proc.stderr
                )
            PYTHON_VERSIONS[binary] = None
            return None

        declared = Version(match.group(1))
        LOG.debug("found %s version %s", binary, declared)

        PYTHON_VERSIONS[binary] = declared

    return PYTHON_VERSIONS[binary]


def find_runtime(
    version: Version, venv: Optional[Path] = None
) -> Tuple[Optional[Path], Optional[Version]]:
    if venv and venv.is_dir():
        bin_dir = venv_bin_path(venv)
        binary_path_str = shutil.which("python", path=bin_dir.as_posix())
        if binary_path_str:
            binary_path = Path(binary_path_str)
            binary_version = runtime_version(binary_path)
            return binary_path, binary_version

    # TODO: better way to find specific micro/pre/post versions?
    binary_names = [
        f"python{version.major}.{version.minor}",
        f"python{version.major}",
        "python",
    ]
    for binary in binary_names:
        binary_path_str = shutil.which(binary)
        LOG.debug("which(%s) -> %s", binary, binary_path_str)
        if binary_path_str is not None:
            binary_path = Path(binary_path_str)
            binary_version = runtime_version(binary_path)

            if binary_version is None:
                continue

            if version_match([binary_version], version):
                return binary_path, binary_version

    return None, None


@timed("resolve contexts")
def resolve_contexts(config: Config, options: Options) -> List[Context]:
    if options.live or not config.versions:
        version = Version(platform.python_version().rstrip("+"))
        # defer resolving python path to after venv creation
        return [Context(version, Path(""), venv_path(config, version), live=True)]

    contexts: List[Context] = []
    missing_versions: List[Version] = []
    for version in config.versions:
        runtime_path, runtime_version = find_runtime(version)

        if runtime_path is None or runtime_version is None:
            missing_versions.append(version)
        else:
            venv = venv_path(config, runtime_version)
            contexts.append(Context(runtime_version, runtime_path, venv))

    if missing_versions:
        LOG.warning("missing Python versions: %r", [str(v) for v in missing_versions])

    context_versions = [context.python_version for context in contexts]
    LOG.info("Available Python versions: %s", context_versions)

    if options.python is not None:
        matched_versions = version_match(context_versions, options.python)
        contexts = [
            context
            for context in contexts
            if context.python_version in matched_versions
        ]

    return contexts


def project_requirements(config: Config) -> Sequence[Path]:
    """Get a list of Path objects for configured or discovered requirements files"""
    paths: List[Path] = []
    if config.requirements:
        paths += [(config.root / req) for req in config.requirements]
    else:
        paths += [req for req in config.root.glob("requirements*.txt")]
    return paths


def pyproject_hash(config: Config) -> str:
    """Return a stable hash of selected ``pyproject.toml`` sections."""
    pyproject = config.root / "pyproject.toml"
    if not pyproject.exists():
        return ""

    content = pyproject.read_text()
    try:
        data = tomli.loads(content)
    except tomli.TOMLDecodeError:
        return ""

    selected: Dict[str, Any] = {}
    for key in PROJECT_REBUILD_KEYS:
        parts = key.split(".")
        current = data
        for part in parts:
            if not isinstance(current, Mapping) or part not in current:
                current = None
                break
            current = current[part]
        if current is not None:
            selected[key] = current

    text = json.dumps(selected, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def needs_update(context: Context, config: Config) -> bool:
    """Compare stored build hash and requirements timestamps"""
    try:
        timestamp = context.venv / TIMESTAMP
        hash_file = context.venv / PYPROJECT_HASH

        if timestamp.exists() and hash_file.exists():
            base = timestamp.stat().st_mtime_ns
            newest = 0
            for path in project_requirements(config):
                if path.exists():
                    newest = max(newest, path.stat().st_mtime_ns)

            if newest > base:
                return True

            stored_hash = hash_file.read_text().strip()
            current_hash = pyproject_hash(config)
            return stored_hash != current_hash

        else:
            LOG.debug("no state for %s", context.venv)

    except Exception:
        LOG.warning(
            "Failed to read virtualenv state for %s",
            context.venv,
            exc_info=True,
        )

    return True


@timed("prepare virtualenv")
async def prepare_virtualenv(context: Context, config: Config) -> AsyncIterator[Event]:
    """Setup virtualenv and install packages"""

    try:
        if needs_update(context, config):
            LOG.info("preparing virtualenv %s", context.venv)
            yield VenvCreate(context, message="creating virtualenv")

            # create virtualenv
            prompt = f"thx-{context.python_version}"
            if context.live:
                import venv

                venv.create(
                    context.venv,
                    prompt=prompt,
                    with_pip=True,
                    symlinks=(os.name != "nt"),
                )

            else:
                await check_command(
                    [
                        context.python_path,
                        "-m",
                        "venv",
                        "--prompt",
                        prompt,
                        context.venv,
                    ]
                )

            new_python_path, new_python_version = find_runtime(
                context.python_version, context.venv
            )
            context.python_path = new_python_path or context.python_path
            context.python_version = new_python_version or context.python_version

            # upgrade pip
            yield VenvCreate(context, message="upgrading pip")
            await check_command(
                [context.python_path, "-m", "pip", "install", "-U", "pip", "setuptools"]
            )
            pip = which("pip", context)

            # install requirements.txt
            requirements = project_requirements(config)
            if requirements:
                yield VenvCreate(context, message="installing requirements")
                LOG.debug("installing deps from %s", requirements)
                cmd: List[StrPath] = [pip, "install", "-U"]
                for requirement in requirements:
                    cmd.extend(["-r", requirement])
                await check_command(cmd)

            # install local project
            yield VenvCreate(context, message="installing project")
            if config.extras:
                proj = f"{config.root}[{','.join(config.extras)}]"
            else:
                proj = str(config.root)
            await check_command([pip, "install", "--editable", proj])

            # timestamp marker
            content = f"{time.time_ns()}\n"
            (context.venv / TIMESTAMP).write_text(content)
            (context.venv / PYPROJECT_HASH).write_text(pyproject_hash(config))

        else:
            LOG.debug("reusing existing virtualenv %s", context.venv)

        yield VenvReady(context)

    except CommandError as error:
        yield VenvError(context, error)


@timed("prepare contexts")
async def prepare_contexts(
    contexts: Sequence[Context], config: Config
) -> AsyncIterator[Event]:
    gens = [prepare_virtualenv(context, config) for context in contexts]
    async for event in as_generated(gens):
        yield event
