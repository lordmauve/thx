# Repository Guidelines

This document helps contributors work effectively in this repository.

## Project Structure & Module Organization

- Source: `thx/` (package modules like `cli.py`, `core.py`, `config.py`).
- Tests: `thx/tests/` (unittest-based suites per module).
- Docs: `docs/` (Sphinx), built into `html/`.
- Tooling/config: `pyproject.toml`, `makefile`, `.flake8`.

## Build, Test, and Development Commands

- Environment: `make venv` then `source .venv/bin/activate`.
- Install dev deps: `make install` (editable with extras `dev,docs`).
- Format: `make format` or `thx format`.
- Lint: `make lint` or `thx lint` (flake8, ufmt, mypy).
- Test + coverage: `make test` or `thx test` then `thx coverage`.
- Docs: `make html` or `thx docs`.

`thx` also supports running multiple jobs: `thx test lint`.

## Coding Style & Naming Conventions

- Python ≥ 3.8. Use type hints; mypy runs in strict mode (see `pyproject.toml`).
- Formatting via `ufmt` (Black + usort). Max line length: 88 (`.flake8`).
- 4‑space indentation; imports are grouped/sorted; no unused imports.
- Naming: modules/functions `snake_case`, classes `CapWords`, constants `UPPER_CASE`.

## Testing Guidelines

- Framework: `unittest` with coverage (`coverage` config in `pyproject.toml`).
- Coverage: target ≥ 90% (build fails under that).
- Test layout: mirror package structure in `thx/tests/`.
- Naming: test files match module names; methods start with `test_`.
- Run: `python -m unittest -v thx.tests` or `make test`.

## Commit & Pull Request Guidelines

- Commits: concise, imperative subject; add context in body if needed.
  Examples: `fix lint`, `rtd config`, `Bump rich to 13.7.1`.
- Reference issues/PRs with `#123` when applicable.
- Before opening a PR: run `make format lint test` and ensure docs build.
- PRs should include: clear description, rationale, screenshots (if UI), and
  notes on behavior or configuration changes.

## Security & Configuration Tips

- Do not commit secrets or local paths; configuration lives in `[tool.thx]` in
  `pyproject.toml`. Jobs can interpolate `{values}` like `{module}` and `{srcs}`.
- Supported Python versions are listed under `tool.thx.python_versions`.
