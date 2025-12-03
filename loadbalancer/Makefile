PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PORT := 8080
BACKENDS := localhost:8000 localhost:8001 localhost:8002

.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: start
start:
	$(PYTHON_VENV) loadbalancer.py $(PORT) $(BACKENDS)

.PHONY: stop
stop:
	pkill -f "loadbalancer.py" || true

.PHONY: lint
lint:
	$(PYTHON_VENV) -m ruff check .
	$(PYTHON_VENV) -m ruff format --check .
	$(PYTHON_VENV) -m mypy .

.PHONY: format
format:
	$(PYTHON_VENV) -m ruff format .
	$(PYTHON_VENV) -m ruff check --fix .
