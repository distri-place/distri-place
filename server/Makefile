PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PORT := 8000
HOST := 0.0.0.0
NODE_ID := node-1

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

.PHONY: start-node
start-node:
	$(PYTHON_VENV) -m app.main --node-id $(NODE_ID) --port $(PORT) --host $(HOST)

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
	$(PYTHON_VENV) -m grpc_tools.protoc --python_out=generated/grpc --pyi_out=generated/grpc --grpc_python_out=generated/grpc --proto_path=. proto/messages.proto
