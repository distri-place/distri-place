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

.PHONY: start-nodes
start-nodes:
	$(PYTHON_VENV) scripts/start_cluster.py

.PHONY: stop-nodes
stop-nodes:
	pkill -f "app.main --node-id" || true

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

.PHONY: generate-grpc
generate-grpc:
	$(PYTHON_VENV) -m grpc_tools.protoc --python_out=app/generated/grpc --pyi_out=app/generated/grpc --grpc_python_out=app/generated/grpc --proto_path=proto proto/messages.proto
