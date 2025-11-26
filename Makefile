# Local development (with Docker nodes)
.PHONY: dev-build
dev-build:
	docker compose build

.PHONY: dev-up
dev-up: dev-build
	docker compose up -d

.PHONY: dev-down
dev-down:
	docker compose down

.PHONY: dev-logs
dev-logs:
	docker compose logs -f

# Client for VM deployment
.PHONY: client-up
client-up:
	docker compose up -d client

.PHONY: client-down
client-down:
	docker compose stop client
	docker compose rm -f client

.PHONY: client-logs
client-logs:
	docker compose logs -f client

# Demo workflow
.PHONY: demo
demo:
	./scripts/tmux-vms.sh

.PHONY: test-ssh
test-ssh:
	./scripts/test-ssh.sh
