PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PORT := 8080
SERVERS := localhost:8000 localhost:8001 localhost:8002

VM1_HOST=svm-11.cs.helsinki.fi
VM2_HOST=svm-11-2.cs.helsinki.fi
VM3_HOST=svm-11-3.cs.helsinki.fi
SERVERS_DEMO=$(VM1_HOST):8000,$(VM2_HOST):8000,$(VM3_HOST):8000

.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

.PHONY: setup-prod
setup-prod:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

.PHONY: start
start:
	$(PYTHON_VENV) -m app.main $(PORT) $(SERVERS)

.PHONY: start-demo
start-demo:
	export SERVERS="$(SERVERS_DEMO)" && \
	$(PYTHON_VENV) -m app.main $(PORT) $(SERVERS_DEMO)

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
