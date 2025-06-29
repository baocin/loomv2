# Makefile for ingestion API service

.PHONY: help test lint docker helm install-dev clean

# Default target
help:
	@echo "Available targets:"
	@echo "  test          - Run unit and integration tests"
	@echo "  lint          - Run black and ruff linting"
	@echo "  docker        - Build Docker image via BuildKit"
	@echo "  helm          - Lint Helm chart"
	@echo "  install-dev   - Install development dependencies"
	@echo "  clean         - Clean up build artifacts"

# Install development dependencies
install-dev:
	uv venv .venv
	. .venv/bin/activate && uv pip install -e .[dev]

# Run tests
test:
	@echo "Running unit tests..."
	pytest tests/unit/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "Running integration tests..."
	pytest tests/integration/ -v

# Run linting
lint:
	@echo "Running black formatter..."
	black app/ tests/
	@echo "Running ruff linter..."
	ruff check app/ tests/ --fix
	@echo "Running ruff format..."
	ruff format app/ tests/

# Check linting without fixing
lint-check:
	@echo "Checking black formatting..."
	black --check app/ tests/
	@echo "Checking ruff linting..."
	ruff check app/ tests/
	@echo "Checking ruff formatting..."
	ruff format --check app/ tests/

# Build Docker image
docker:
	@echo "Building Docker image with BuildKit..."
	DOCKER_BUILDKIT=1 docker build \
		--build-arg GIT_COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo "unknown") \
		--build-arg GIT_BRANCH=$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown") \
		--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
		--build-arg BUILD_VERSION=$$(git describe --tags --always 2>/dev/null || echo "latest") \
		-t loom-ingestion-api:latest \
		-t loom-ingestion-api:$$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
		.

# Inspect Docker image labels
docker-inspect:
	@echo "Docker image labels for loom-ingestion-api:latest"
	@docker inspect loom-ingestion-api:latest --format '{{json .Config.Labels}}' | jq .

# Lint Helm chart (when created)
helm:
	@echo "Linting Helm chart..."
	@if [ -d "charts" ]; then \
		helm lint charts/*; \
		helm template charts/* --dry-run; \
	else \
		echo "No Helm charts found in charts/ directory"; \
	fi

# Run type checking
type-check:
	@echo "Running mypy type checking..."
	mypy app/ --ignore-missing-imports

# Clean up build artifacts
clean:
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development server with hot reload
dev:
	@echo "Starting development server..."
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run security checks
security:
	@echo "Running security checks..."
	safety check
	bandit -r app/

# Full CI pipeline (what CI should run)
ci: lint-check type-check test security
	@echo "All CI checks passed!"

# Generate requirements-locked.txt
lock:
	uv pip compile pyproject.toml -o requirements-locked.txt
