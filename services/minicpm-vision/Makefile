.PHONY: help install dev test test-watch test-coverage lint format type-check security ci docker docker-run clean

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
UV := uv
SERVICE_NAME := minicpm-vision
DOCKER_IMAGE := loom/$(SERVICE_NAME):latest
DOCKER_REGISTRY := localhost:5000

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install dependencies
	$(UV) pip install -e ".[dev]"

requirements: ## Generate requirements.txt
	$(UV) pip compile pyproject.toml -o requirements.txt

requirements-lock: ## Generate locked requirements
	$(UV) pip freeze > requirements-locked.txt

dev: ## Run development server with hot-reload
	LOOM_ENVIRONMENT=development $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run unit tests
	$(UV) run pytest tests/unit -v

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch tests/unit -v

test-coverage: ## Run tests with coverage report
	$(UV) run pytest tests/unit --cov=app --cov-report=html --cov-report=term

test-integration: ## Run integration tests
	$(UV) run pytest tests/integration -v

lint: ## Run linters
	$(UV) run ruff check app tests
	$(UV) run black --check app tests

lint-fix: ## Fix linting issues
	$(UV) run ruff check --fix app tests
	$(UV) run black app tests

format: lint-fix ## Format code

type-check: ## Run type checking
	$(UV) run mypy app

security: ## Run security checks
	$(UV) run bandit -r app
	$(UV) run safety check

ci: lint type-check test security ## Run full CI pipeline

docker: ## Build Docker image
	docker build -t $(DOCKER_IMAGE) .

docker-push: docker ## Push Docker image to registry
	docker tag $(DOCKER_IMAGE) $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)
	docker push $(DOCKER_REGISTRY)/$(DOCKER_IMAGE)

docker-run: ## Run Docker container locally
	docker run --rm -it \
		-p 8000:8000 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e LOOM_LOG_LEVEL=INFO \
		$(DOCKER_IMAGE)

clean: ## Clean build artifacts
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
