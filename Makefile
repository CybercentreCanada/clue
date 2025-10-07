SHELL = /bin/bash

.PHONY: setup
setup: ## Install dependencies for both UI and API components
	@echo "Setting up development environment..."

	# Check and install pnpm if needed
	@if ! command -v pnpm >/dev/null 2>&1; then \
		echo "Installing pnpm..."; \
		npm install --global corepack@latest; \
		corepack enable pnpm; \
	else \
		echo "✅ pnpm is already installed"; \
	fi

	# Check and install poetry if needed
	@if ! command -v poetry >/dev/null 2>&1; then \
		echo "Installing poetry..."; \
		python -m pip install poetry; \
	else \
		echo "✅ poetry is already installed"; \
	fi

	# Install UI dependencies
	@echo "Installing UI dependencies..."
	cd ui && pnpm install

	# Install API dependencies
	@echo "Installing API dependencies..."
	cd api && poetry install --all-extras --with test,dev,types

	@echo "🎉 Setup complete!"

.PHONY: start-dependencies
start-dependencies: ## Start development dependencies (Redis, Keycloak) in Docker
	@echo "Starting development dependencies..."
	cd api/dev && docker compose up --build -d
	@echo "✅ Dependencies are running in the background"

.PHONY: stop-dependencies
stop-dependencies: ## Stop development dependencies (Redis, Keycloak) in Docker
	@echo "Stopping development dependencies..."
	cd api/dev && docker compose down
	@echo "✅ Dependencies have been stopped"

.PHONY: help
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'
