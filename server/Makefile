PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PORT := 8000
HOST := 0.0.0.0

.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

.PHONY: install
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

.PHONY: dev
dev:
	$(PYTHON_VENV) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

.PHONY: test
test:
	$(PYTHON_VENV) -m pytest tests/ -v

.PHONY: lint
lint:
	$(PYTHON_VENV) -m ruff check app/
	$(PYTHON_VENV) -m ruff format --check app/
	$(PYTHON_VENV) -m mypy app/

.PHONY: format
format:
	$(PYTHON_VENV) -m ruff format app/
	$(PYTHON_VENV) -m ruff check --fix app/
