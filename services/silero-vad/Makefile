.PHONY: help install dev test test-watch test-coverage lint format type-check security docker docker-run clean ci

PYTHON := python3
UV := uv
SERVICE_NAME := silero-vad
DOCKER_IMAGE := loomv2/$(SERVICE_NAME)
DOCKER_TAG := latest

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using uv
	$(UV) venv
	$(UV) pip install -e ".[dev]"

requirements: ## Generate requirements.txt from pyproject.toml
	$(UV) pip compile pyproject.toml -o requirements.txt

dev: ## Run development server with hot-reload
	$(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

test: ## Run unit tests
	$(UV) run pytest tests/unit -v

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch tests/unit -v

test-coverage: ## Run tests with coverage report
	$(UV) run pytest tests/unit --cov=app --cov-report=html --cov-report=term

test-integration: ## Run integration tests
	$(UV) run pytest tests/integration -v

lint: ## Run linting with ruff
	$(UV) run ruff check app tests
	$(UV) run ruff format --check app tests

lint-fix: ## Fix linting issues
	$(UV) run ruff check --fix app tests
	$(UV) run ruff format app tests

format: lint-fix ## Format code (alias for lint-fix)

type-check: ## Run type checking with mypy
	$(UV) run mypy app

security: ## Run security checks
	$(UV) run bandit -r app -ll

docker: ## Build Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run: ## Run Docker container locally
	docker run --rm -it \
		-p 8001:8001 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		--name $(SERVICE_NAME) \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

clean: ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage

ci: lint type-check test security ## Run full CI pipeline
