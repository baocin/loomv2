# Makefile for Gemma 3N Processor Service

.PHONY: help install dev build test test-unit test-integration test-coverage lint format security docker clean

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
install: ## Install dependencies with uv
	uv sync --all-extras

dev: ## Run development server with hot-reload
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

build: ## Build the application (no-op for Python, but useful for CI)
	@echo "Building Gemma 3N Processor..."
	uv sync --locked

# Testing
test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	uv run pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v

test-watch: ## Run tests in watch mode
	uv run pytest-watch tests/ -- -v

# Code quality
lint: ## Run linting checks
	uv run ruff check .
	uv run mypy app/

lint-fix: ## Fix linting issues
	uv run ruff check --fix .
	uv run ruff format .

format: ## Format code
	uv run black .
	uv run ruff format .

type-check: ## Run type checking
	uv run mypy app/

security: ## Run security scans
	uv run bandit -r app/
	uv run safety check

# CI pipeline
ci: lint type-check test security ## Run full CI pipeline

# Docker
docker: ## Build Docker image
	docker build -t loom/gemma3n-processor:latest .

docker-run: ## Run Docker container locally
	docker run -p 8000:8000 -p 11434:11434 \
		-e LOOM_LOG_LEVEL=DEBUG \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		loom/gemma3n-processor:latest

docker-test: ## Run tests in Docker container
	docker run --rm loom/gemma3n-processor:latest uv run pytest tests/ -v

# Kubernetes
k8s-deploy: ## Deploy to local k3d cluster
	kubectl apply -f ../../deploy/dev/gemma3n-processor.yaml

k8s-delete: ## Delete from k3d cluster
	kubectl delete -f ../../deploy/dev/gemma3n-processor.yaml --ignore-not-found

k8s-logs: ## View pod logs
	kubectl logs -f -l app=gemma3n-processor -n loom-dev

k8s-status: ## Check deployment status
	kubectl get pods,svc -l app=gemma3n-processor -n loom-dev

# Local testing with Ollama
ollama-install: ## Install Ollama locally (requires curl)
	curl -fsSL https://ollama.com/install.sh | sh

ollama-start: ## Start Ollama server locally
	ollama serve &

ollama-pull: ## Pull Gemma 3N model
	ollama pull gemma3n:e4b

ollama-test: ## Test Ollama with Gemma 3N
	ollama run gemma3n:e4b "Explain multimodal AI in one sentence."

# Cleanup
clean: ## Clean up generated files
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-docker: ## Clean up Docker images
	docker rmi loom/gemma3n-processor:latest || true
	docker system prune -f

# Requirements
requirements: ## Generate requirements.txt (for compatibility)
	uv export --format requirements-txt > requirements.txt

# Health checks
health: ## Check service health (requires running service)
	curl -f http://localhost:8000/healthz || echo "Service not running"

ready: ## Check service readiness (requires running service)
	curl -f http://localhost:8000/readyz || echo "Service not ready"

status: ## Get service status (requires running service)
	curl -s http://localhost:8000/status | python -m json.tool || echo "Service not available"

# Performance testing
load-test: ## Run basic load test (requires hey tool)
	hey -n 100 -c 10 http://localhost:8000/healthz

# Documentation
docs: ## Generate API documentation
	@echo "API documentation available at http://localhost:8000/docs when service is running"