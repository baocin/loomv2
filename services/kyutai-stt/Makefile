.PHONY: help install dev test test-watch test-coverage lint format type-check security docker docker-run clean

# Default target
.DEFAULT_GOAL := help

# Service name
SERVICE_NAME := kyutai-stt
DOCKER_IMAGE := loomv2/$(SERVICE_NAME):latest

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install dependencies using uv
	uv pip install -e ".[dev]"

dev: ## Run development server with hot reload
	LOOM_LOG_LEVEL=DEBUG uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

requirements: ## Generate requirements.txt from pyproject.toml
	uv pip compile pyproject.toml -o requirements.txt

test: ## Run unit tests
	pytest tests/unit -v

test-watch: ## Run tests in watch mode
	pytest-watch tests/unit -v

test-coverage: ## Run tests with coverage report
	pytest tests/unit --cov=app --cov-report=html --cov-report=term -v

test-integration: ## Run integration tests
	pytest tests/integration -v

test-model: ## Test Kyutai model loading
	python test_kyutai_model.py

lint: ## Run linting tools
	ruff check app tests
	black --check app tests

lint-fix: ## Fix linting issues
	ruff check --fix app tests
	black app tests

format: lint-fix ## Format code (alias for lint-fix)

type-check: ## Run type checking with mypy
	mypy app

security: ## Run security checks
	pip-audit

ci: lint type-check test security ## Run full CI pipeline

docker: ## Build Docker image
	docker build -t $(DOCKER_IMAGE) .

docker-gpu: ## Build Docker image with GPU support
	docker build -t $(DOCKER_IMAGE)-gpu --build-arg BASE_IMAGE=nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 .

docker-run: ## Run Docker container locally
	docker run -it --rm \
		-p 8002:8002 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e LOOM_LOG_LEVEL=DEBUG \
		$(DOCKER_IMAGE)

docker-run-gpu: ## Run Docker container with GPU support
	docker run -it --rm \
		--gpus all \
		-p 8002:8002 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e LOOM_LOG_LEVEL=DEBUG \
		$(DOCKER_IMAGE)-gpu

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
