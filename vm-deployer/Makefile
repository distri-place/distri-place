PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python

.PHONY: setup
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: install
install:
	$(PIP) install --upgrade pip

.PHONY: deploy
deploy:
	$(PYTHON) deploy.py

.PHONY: test-ssh
test-ssh:
	$(PYTHON) deploy.py test-ssh

.PHONY: clean
clean:
	rm -rf $(VENV)
	pkill -f "deploy.py" || true