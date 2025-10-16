SHELL = /bin/bash

.PHONY: setup
setup: ## Install dependencies for both UI and API components
	@echo "Setting up development environment..."

	@if ! command -v pnpm >/dev/null 2>&1; then \
		@echo "Installing pnpm..."; \
		@echo -n "⏩ "; \
		npm install --global corepack@latest; \
		corepack enable pnpm; \
	else \
		echo "✅ pnpm is already installed"; \
	fi

	@if ! command -v poetry >/dev/null 2>&1; then \
		@echo "Installing poetry..."; \
		@echo -n "⏩ "; \
		python -m pip install poetry; \
	else \
		echo "✅ poetry is already installed"; \
	fi

	@echo "Installing UI dependencies..."
	@echo -n "⏩ "
	cd ui && pnpm install

	@echo "Installing API dependencies..."
	@echo -n "⏩ "
	cd api && poetry install --all-extras --with test,dev,types

	@echo "🎉 Setup complete!"

.PHONY: start-dependencies
start-dependencies: ## Start development dependencies (Redis, Keycloak) in Docker
	@echo "Starting development dependencies..."
	@echo -n "⏩ "
	cd api/dev && docker compose up --build -d
	@echo "✅ Dependencies are running in the background"

.PHONY: stop-dependencies
stop-dependencies: ## Stop development dependencies (Redis, Keycloak) in Docker
	@echo "Stopping development dependencies..."
	@echo -n "⏩ "
	cd api/dev && docker compose down
	@echo "✅ Dependencies have been stopped"

.PHONY: test-plugin
test-plugin: ## Run a specific plugin interactively (usage: make test-plugin <plugin-name>)
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "❌ Error: Plugin name is required. Usage: make test-plugin <plugin-name>"; \
		exit 1; \
	fi
	@echo "✅ Running plugin: $(filter-out $@,$(MAKECMDGOALS))"
	@echo -n "⏩ "
	cd plugins/setup && python interactive.py $(filter-out $@,$(MAKECMDGOALS))

.PHONY: create-plugin
create-plugin: ## Create a new plugin
	@cd plugins/setup && python create.py

.PHONY: help
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}'
