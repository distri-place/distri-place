# Local development (with Docker nodes)
.PHONY: dev-build
dev-build:
	docker compose --profile dev build

.PHONY: dev-up
dev-up: dev-build
	docker compose --profile dev up -d

.PHONY: dev-down
dev-down:
	docker compose --profile dev down

.PHONY: dev-logs
dev-logs:
	docker compose --profile dev logs -f

# Client for VM deployment
.PHONY: client-up
client-up:
	@echo "Starting client for VM deployment..."
	@if [ ! -f nginx/nginx-vm.conf ]; then \
		echo "Error: VM nginx config not found. Run 'make vm-up' first."; \
		exit 1; \
	fi
	docker compose --profile vm up -d nginx-vm
	@echo "Client available at: http://localhost:8080"

.PHONY: client-down
client-down:
	docker compose --profile vm down

.PHONY: client-logs
client-logs:
	docker compose --profile vm logs -f nginx-vm

# VM Deployment targets
.PHONY: vm-up
vm-up:
	@echo "Deploying to VMs..."
	@if [ ! -f vm-config.env ]; then \
		echo "Error: No VM configuration found. Copy vm-config.example.env to vm-config.env and update it."; \
		exit 1; \
	fi
	./scripts/deploy-vms.sh deploy

.PHONY: vm-test-ssh
vm-test-ssh:
	@echo "Testing SSH connections to VMs..."
	./scripts/deploy-vms.sh test-ssh

.PHONY: vm-status
vm-status:
	@echo "Checking VM deployment status..."
	@./scripts/vm-status.sh

.PHONY: vm-logs
vm-logs:
	@echo "Fetching logs from VMs..."
	@./scripts/vm-logs.sh

.PHONY: vm-down
vm-down:
	@echo "Cleaning up VM deployment..."
	@./scripts/vm-clean.sh

# Demo workflow
.PHONY: demo-deploy
demo-deploy: vm-up client-up
	@echo "Demo deployment complete!"

.PHONY: demo-clean
demo-clean: client-down vm-down
	@echo "Demo environment cleaned up"
