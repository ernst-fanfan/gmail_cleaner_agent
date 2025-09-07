.DEFAULT_GOAL := help

IMAGE ?= cleanmail:local
TZ ?= America/New_York

.PHONY: help build run-serve run-dry compose-build compose-up compose-dev dev-sh test

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-16s\033[0m %s\n", $$1, $$2}' | sort

build: ## Build Docker image (IMAGE=$(IMAGE))
	docker build -t $(IMAGE) .

run-serve: ## Run scheduler service (serve) in a container
	docker run --rm \
	  -e TZ=$(TZ) \
	  -e OPENAI_API_KEY=$${OPENAI_API_KEY:-} \
	  -v "$$(pwd)/config.yaml:/app/config.yaml:ro" \
	  -v "$$(pwd)/data:/app/data" \
	  -v "$$(pwd)/reports:/app/reports" \
	  $(IMAGE) \
	  python -m cleanmail.main serve

run-dry: ## One-off dry run
	docker run --rm \
	  -e TZ=$(TZ) \
	  -e OPENAI_API_KEY=$${OPENAI_API_KEY:-} \
	  -v "$$(pwd)/config.yaml:/app/config.yaml:ro" \
	  -v "$$(pwd)/data:/app/data" \
	  -v "$$(pwd)/reports:/app/reports" \
	  $(IMAGE) \
	  python -m cleanmail.main run --dry-run

compose-build: ## Build images via Docker Compose
	docker compose build

compose-up: ## Start scheduler via Docker Compose
	docker compose up cleanmail

compose-dev: ## Start dev container (sleep infinity)
	docker compose up -d dev

dev-sh: ## Open a shell in the dev container
	docker compose exec dev bash

test: ## Run tests in Docker Compose
	docker compose run --rm tests

