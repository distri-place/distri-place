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

.PHONY: dev
dev: dev-up dev-logs

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

.PHONY: setup-ssh
setup-ssh:
	./scripts/setup-ssh-keys.sh

.PHONY: test-ssh
test-ssh:
	./scripts/test-ssh.sh

# For docs
.PHONY: generate-final-report-pdf
generate-final-report-pdf:
	pandoc docs/final_report.md \
		-o docs/final_report.pdf \
		--filter mermaid-filter \
		--table-of-contents \
		--toc-depth=3 \
		--number-sections \
		--top-level-division=chapter \
        -V geometry:margin=1in \
		-V toc-title="Table of Contents" \
		-V toc-own-page=true \
		-V linkcolor=blue \
		-V urlcolor=blue \
		-V titlepage=true \
		-V title="Distri-place - Final report" \
		-V author="Viljami Ranta, Ilari Heikkinen, Antti Ollikkala, Joni Pesonen" \
		-V date="$(date +'%B %Y')"
