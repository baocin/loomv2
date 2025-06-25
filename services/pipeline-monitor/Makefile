# Pipeline Monitor Makefile
.PHONY: help install dev build docker docker-run clean lint format type-check test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm ci

dev: ## Start development server
	npm run dev

build: ## Build for production
	npm run build

lint: ## Run linter
	npm run lint

format: ## Format code
	npx prettier --write src/

type-check: ## Run TypeScript type checking
	npx tsc --noEmit

test: ## Run tests
	npm run test

test-ui: ## Run tests with UI
	npm run test:ui

docker: ## Build Docker image
	docker build -t loom/pipeline-monitor:latest .

docker-run: ## Run Docker container locally
	docker run --rm -p 3000:3000 \
		-e VITE_API_URL=http://localhost:8080 \
		loom/pipeline-monitor:latest

clean: ## Clean build artifacts
	rm -rf dist node_modules

ci: lint type-check test build ## Run full CI pipeline
