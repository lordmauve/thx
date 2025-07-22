# thx Project Overview

## Mission

`thx` is a fast command runner and development assistant for Python projects. It
allows projects to define reusable **jobs** in `pyproject.toml` and run them
across multiple Python versions. Jobs can be chained, run in parallel, and
executed automatically when files change via watch mode.

## Development Practices

- Requires Python 3.8 or newer.
- Dependencies for development are listed under the `dev` and `docs` extras in
  `pyproject.toml`.
- Use the `makefile` for common tasks:
  - `make install` – install project with development extras
  - `make format` – format code with `ufmt`
  - `make lint` – run `flake8` and `ufmt` checks
  - `make test` – run the unit test suite and coverage
  - `make html` – build the Sphinx documentation
  - `make clean`/`distclean` – remove build artifacts and the virtualenv
- Bootstrap a virtual environment and install development requirements before
  working on the project.
- Run `thx` to format, lint, and test the code before submitting a pull request.
- Document user-facing changes in ``README.rst`` and add license headers to new
  files.
- The changelog is generated automatically by the `attribution` tool; do not
  edit ``CHANGELOG.md`` manually.

## Code Style

- Source is formatted with `ufmt` and checked with `flake8`.
- Static type checking is performed with `mypy`.
- Tests use `coverage` and must maintain at least 90% coverage (see
  `[tool.coverage]` in `pyproject.toml`).
- The repository includes a `py.typed` marker and uses type hints throughout.

## Code Structure

```
├── thx/                # main package
│   ├── __init__.py
│   ├── __main__.py     # entry point
│   ├── cli.py          # Rich-based CLI renderer
│   ├── config.py       # parsing and validating pyproject configuration
│   ├── context.py      # virtualenv and runtime management
│   ├── core.py         # job orchestration and watch mode
│   ├── main.py         # Click command definitions
│   ├── runner.py       # command execution helpers
│   ├── types.py        # shared dataclasses and type definitions
│   └── utils.py        # timing and helper utilities
├── docs/               # Sphinx documentation sources
├── CHANGELOG.md
├── CONTRIBUTING.md
├── makefile
└── pyproject.toml      # project metadata and thx configuration
```

Unit tests live under `thx/tests` and cover configuration parsing, context
handling, CLI rendering, runners, and utility functions.
