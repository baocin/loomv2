# Makefile for georegion-detector service

.PHONY: help install dev test docker clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server"
	@echo "  make test       - Run tests"
	@echo "  make docker     - Build Docker image"
	@echo "  make clean      - Clean up generated files"

install:
	pip install -r requirements.txt

dev:
	LOOM_LOG_LEVEL=DEBUG python -m app.main

test:
	pytest tests/ -v

docker:
	docker build -t loom/georegion-detector:latest .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete