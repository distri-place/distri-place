PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PORT := 8000
HOST := 0.0.0.0
NODE_ID := node-1

VM1_HOST=svm-11.cs.helsinki.fi
VM2_HOST=svm-11-2.cs.helsinki.fi
VM3_HOST=svm-11-3.cs.helsinki.fi
GATEWAY_HOST=melkki.cs.helsinki.fi

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

.PHONY: start-node-1
start-node-1:
	export LOG_LEVEL="DEBUG" && \
	export NODE_ID="node-1" && \
	export HTTP_PORT=8000 && \
	export GRPC_PORT=8001 && \
	export HOST="0.0.0.0" && \
	export PEERS="node-2:$(VM2_HOST):8000:8001,node-3:$(VM3_HOST):8000:8001" && \
	$(PYTHON_VENV) -m app.main

.PHONY: start-node-2
start-node-2:
	export LOG_LEVEL="DEBUG" && \
	export NODE_ID="node-2" && \
	export HTTP_PORT=8000 && \
	export GRPC_PORT=8001 && \
	export HOST="0.0.0.0" && \
	export PEERS="node-1:$(VM1_HOST):8000:8001,node-3:$(VM3_HOST):8000:8001" && \
	$(PYTHON_VENV) -m app.main

.PHONY: start-node-3
start-node-3:
	export LOG_LEVEL="DEBUG" && \
	export NODE_ID="node-3" && \
	export HTTP_PORT=8000 && \
	export GRPC_PORT=8001 && \
	export HOST="0.0.0.0" && \
	export PEERS="node-1:$(VM1_HOST):8000:8001,node-2:$(VM2_HOST):8000:8001" && \
	$(PYTHON_VENV) -m app.main

.PHONY: stop-nodes
stop-nodes:
	pkill -f "app.main --node_id" || true

.PHONY: test
test:
	$(PYTHON_VENV) -m pytest tests/ -v

.PHONY: lint
lint:
	$(PYTHON_VENV) -m ruff check app/ --exclude app/generated/
	$(PYTHON_VENV) -m ruff format --check app/ --exclude app/generated/
	$(PYTHON_VENV) -m mypy app/ --exclude app/generated/

.PHONY: format
format:
	$(PYTHON_VENV) -m ruff format app/ --exclude app/generated/
	$(PYTHON_VENV) -m ruff check --fix app/ --exclude app/generated/

.PHONY: generate-grpc
generate-grpc:
	$(PYTHON_VENV) -m grpc_tools.protoc --python_out=app/generated/grpc --pyi_out=app/generated/grpc --grpc_python_out=app/generated/grpc --proto_path=proto proto/messages.proto
