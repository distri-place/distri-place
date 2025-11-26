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
	docker compose up -d nginx-vm

.PHONY: client-down
client-down:
	docker compose --profile vm down

.PHONY: client-logs
client-logs:
	docker compose --profile vm logs -f nginx-vm

# Demo workflow
.PHONY: demo
demo:
	./scripts/tmux-vms.sh
