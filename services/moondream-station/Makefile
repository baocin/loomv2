# Makefile for Moondream Station Service

.PHONY: help install dev build test test-unit test-integration test-coverage lint format security docker clean

# Default target
help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development
install: ## Install dependencies with pip
	pip install -e .[dev]

dev: ## Run development server with hot-reload
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug

build: ## Build the application
	@echo "Building Moondream Station..."
	pip install -e .

# Testing
test: ## Run all tests
	pytest tests/ -v

test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v

test-watch: ## Run tests in watch mode
	pytest-watch tests/ -- -v

# Code quality
lint: ## Run linting checks
	ruff check .
	mypy app/

lint-fix: ## Fix linting issues
	ruff check --fix .
	ruff format .

format: ## Format code
	black .
	ruff format .

type-check: ## Run type checking
	mypy app/

security: ## Run security scans
	bandit -r app/
	safety check

# CI pipeline
ci: lint type-check test security ## Run full CI pipeline

# Docker
docker: ## Build Docker image
	docker build -t loom/moondream-station:latest .

docker-run: ## Run Docker container locally
	docker run -p 8000:8000 -p 2020:2020 \
		-e LOOM_LOG_LEVEL=DEBUG \
		-e LOOM_KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
		loom/moondream-station:latest

docker-test: ## Run tests in Docker container
	docker run --rm loom/moondream-station:latest pytest tests/ -v

# Kubernetes
k8s-deploy: ## Deploy to local k3d cluster
	kubectl apply -f ../../deploy/dev/moondream-station.yaml

k8s-delete: ## Delete from k3d cluster
	kubectl delete -f ../../deploy/dev/moondream-station.yaml --ignore-not-found

k8s-logs: ## View pod logs
	kubectl logs -f -l app=moondream-station -n loom-dev

k8s-status: ## Check deployment status
	kubectl get pods,svc -l app=moondream-station -n loom-dev

# Moondream Station specific
moondream-install: ## Install Moondream Station locally
	curl -fsSL https://depot.moondream.ai/station/install.sh | bash

moondream-test: ## Test local Moondream Station
	@echo "Testing Moondream Station..."
	@curl -s http://localhost:2020/v1/health || echo "Moondream Station not running"

moondream-caption: ## Test image captioning (requires test.jpg)
	@if [ -f test.jpg ]; then \
		curl -X POST http://localhost:8000/caption \
			-F "image=@test.jpg" \
			| python -m json.tool; \
	else \
		echo "Please provide test.jpg for testing"; \
	fi

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
	docker rmi loom/moondream-station:latest || true
	docker system prune -f

# Requirements
requirements: ## Generate requirements.txt
	pip freeze > requirements.txt

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

# API testing
test-api-caption: ## Test caption endpoint with sample image
	@echo "Creating test image..."
	@python -c "from PIL import Image; img = Image.new('RGB', (100, 100), 'red'); img.save('test_api.jpg')"
	curl -X POST http://localhost:8000/caption \
		-F "image=@test_api.jpg" \
		| python -m json.tool
	@rm -f test_api.jpg

test-api-query: ## Test query endpoint with sample image
	@echo "Creating test image..."
	@python -c "from PIL import Image; img = Image.new('RGB', (100, 100), 'blue'); img.save('test_api.jpg')"
	curl -X POST http://localhost:8000/query \
		-F "image=@test_api.jpg" \
		-F "query=What color is this image?" \
		| python -m json.tool
	@rm -f test_api.jpg

test-api-analyze: ## Test analyze endpoint
	@echo "Creating test request..."
	@python -c "import base64; from PIL import Image; from io import BytesIO; \
		img = Image.new('RGB', (100, 100), 'green'); \
		buffer = BytesIO(); img.save(buffer, 'PNG'); \
		data = base64.b64encode(buffer.getvalue()).decode(); \
		import json; \
		req = {'image_data': data, 'query': 'Describe this image'}; \
		print(json.dumps(req))" > test_request.json
	curl -X POST http://localhost:8000/analyze/image \
		-H "Content-Type: application/json" \
		-d @test_request.json \
		| python -m json.tool
	@rm -f test_request.json

# Documentation
docs: ## Generate API documentation
	@echo "API documentation available at http://localhost:8000/docs when service is running"