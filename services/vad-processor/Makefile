# Makefile for VAD Processor Service

.PHONY: help install dev test lint docker run clean

help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies"
	@echo "  dev          - Run development server"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting"
	@echo "  docker       - Build Docker image"
	@echo "  run          - Run with Docker"
	@echo "  clean        - Clean up artifacts"

install:
	uv venv .venv
	. .venv/bin/activate && uv pip install -e .[dev]

dev:
	@echo "Starting VAD processor in development mode..."
	. .venv/bin/activate && python -m app.main

test:
	@echo "Running tests..."
	. .venv/bin/activate && pytest tests/ -v --cov=app

lint:
	@echo "Running linters..."
	. .venv/bin/activate && black app/ tests/
	. .venv/bin/activate && ruff check app/ tests/ --fix
	. .venv/bin/activate && mypy app/

docker:
	@echo "Building Docker image..."
	docker build -t loom-vad-processor:latest .

run:
	@echo "Running VAD processor in Docker..."
	docker run --rm \
		-e VAD_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e VAD_DATABASE_URL=postgresql://loom:loom@host.docker.internal:5432/loom \
		-p 8001:8001 \
		loom-vad-processor:latest

clean:
	@echo "Cleaning up..."
	rm -rf .venv/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
