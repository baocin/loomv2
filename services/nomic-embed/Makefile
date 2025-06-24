# Nomic Embed Vision Service Makefile

.PHONY: help install dev test lint format type-check docker run clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies with uv"
	@echo "  dev         - Run development server with hot reload"
	@echo "  test        - Run unit tests"
	@echo "  lint        - Run linting checks"
	@echo "  format      - Format code with black and ruff"
	@echo "  type-check  - Run mypy type checking"
	@echo "  docker      - Build Docker image"
	@echo "  run         - Run service locally"
	@echo "  clean       - Clean cache and temp files"

# Install dependencies
install:
	uv sync

# Run development server
dev:
	uv run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

# Run tests
test:
	uv run pytest tests/ -v

# Lint code
lint:
	uv run ruff check app/
	uv run black --check app/

# Format code
format:
	uv run black app/
	uv run ruff check --fix app/

# Type checking
type-check:
	uv run mypy app/

# Build Docker image
docker:
	docker build -t loom/nomic-embed:latest .

# Run service locally
run:
	uv run python -m app.main

# Clean cache and temp files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".mypy_cache" -delete
	rm -rf .coverage htmlcov/

# Full CI pipeline
ci: install lint type-check test

# Development setup
setup: install
	@echo "Development environment set up successfully"
	@echo "Run 'make dev' to start the development server"