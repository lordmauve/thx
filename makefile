PKG:=thx
EXTRAS:=dev,docs

# Prefer uv for environment and dependency management
UV:=$(shell uv --version)
PY:=.venv/bin/python

install: .venv  ## Populate venv with project + extras via uv
ifdef UV
	uv sync --extra dev --extra docs
else
	$(PY) -m pip install -Ue .[$(EXTRAS)]
endif

.PHONY: venv
.venv:  ## Create and populate venv (uses uv if available)
ifdef UV
	uv sync --extra dev --extra docs
else
	python -m venv .venv
	$(PY) -m pip install -Ue .[$(EXTRAS)]
endif

venv: .venv
	@echo 'Virtualenv ready. To activate: `source .venv/bin/activate`'

format: .venv
	$(PY) -m ufmt format $(PKG)

lint: .venv
	$(PY) -m flake8 $(PKG)
	$(PY) -m ufmt check $(PKG)

test: .venv
	# Prefer coverage if available; otherwise run tests directly
	@if $(PY) -c "import coverage" >/dev/null 2>&1; then \
		$(PY) -m coverage run -m $(PKG).tests && \
		$(PY) -m coverage combine && \
		$(PY) -m coverage report; \
	else \
		echo "coverage not available; running tests without coverage"; \
		$(PY) -m $(PKG).tests; \
	fi
	# Run mypy if available
	@if $(PY) -c "import mypy" >/dev/null 2>&1; then \
		$(PY) -m mypy --install-types --non-interactive -p $(PKG); \
	else \
		echo "mypy not available; skipping type check"; \
	fi

html: .venv README.rst docs/*.rst docs/conf.py
	.venv/bin/sphinx-build -b html docs html

clean:
	rm -rf build dist html *.egg-info .mypy_cache

distclean: clean
	rm -rf .venv
