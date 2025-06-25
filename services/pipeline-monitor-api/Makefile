# Pipeline Monitor API Makefile
.PHONY: help install dev build docker docker-run clean lint format type-check test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	npm ci

dev: ## Start development server with hot reload
	npm run dev

build: ## Build TypeScript to JavaScript
	npm run build

start: ## Start production server
	npm start

lint: ## Run linter
	npm run lint

format: ## Format code
	npm run format

type-check: ## Run TypeScript type checking
	npm run type-check

test: ## Run tests
	npm run test

test-watch: ## Run tests in watch mode
	npm run test:watch

docker: ## Build Docker image
	docker build -t loom/pipeline-monitor-api:latest .

docker-run: ## Run Docker container locally
	docker run --rm -p 8080:8080 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e LOOM_DATABASE_HOST=host.docker.internal \
		-e LOOM_DATABASE_PORT=5432 \
		-e LOOM_DATABASE_NAME=loom \
		-e LOOM_DATABASE_USER=loom \
		-e LOOM_DATABASE_PASSWORD=loom \
		-e CORS_ORIGIN=http://localhost:3000 \
		loom/pipeline-monitor-api:latest

clean: ## Clean build artifacts
	rm -rf dist node_modules

ci: lint type-check test build ## Run full CI pipeline
