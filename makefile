PKG:=thx
EXTRAS:=dev,docs

UV:=$(shell uv --version)
ifdef UV
	VENV:=uv venv
	PIP:=uv pip
else
	VENV:=python3 -m venv
	PIP:=.venv/bin/python3 -m pip
endif

PYTHON := .venv/bin/python3

.PHONY: .venv install venv format lint test html clean distclean

install: .venv
	$(PIP) install -Ue .[$(EXTRAS)]

.venv:
	$(VENV) .venv

venv: install
	echo 'run `source .venv/bin/activate` to activate virtualenv'

format: venv
	$(PYTHON) -m ufmt format $(PKG)

lint: venv
	$(PYTHON) -m flake8 $(PKG)
	$(PYTHON) -m ufmt check $(PKG)

test: venv
	. .venv/bin/activate && $(PYTHON) -m coverage run -m $(PKG).tests
	$(PYTHON) -m coverage combine
	$(PYTHON) -m coverage report
	$(PYTHON) -m mypy --install-types --non-interactive -p $(PKG)

html: venv README.rst docs/*.rst docs/conf.py
	. .venv/bin/activate && sphinx-build -b html docs html

clean:
	rm -rf build dist html *.egg-info .mypy_cache

distclean: clean
	rm -rf .venv