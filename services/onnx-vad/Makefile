.PHONY: help install dev test lint format type-check docker docker-run clean

help:
	@echo "Available commands:"
	@echo "  install      Install dependencies"
	@echo "  dev          Run development server"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo "  type-check   Run type checking"
	@echo "  docker       Build Docker image"
	@echo "  docker-run   Run Docker container"
	@echo "  clean        Clean up generated files"

install:
	pip install -e .

dev:
	python -m uvicorn app.main:app --reload --port 8001

test:
	pytest tests/ -v

lint:
	ruff check app/

format:
	ruff format app/
	ruff check app/ --fix

type-check:
	mypy app/

docker:
	docker build -t loom/onnx-vad:latest .

docker-run:
	docker run -p 8001:8001 \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		-e LOOM_LOG_LEVEL=DEBUG \
		-e VAD_DEVICE=cpu \
		loom/onnx-vad:latest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .ruff_cache .mypy_cache .pytest_cache
