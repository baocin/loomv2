.PHONY: help setup test lint format docker clean dev-up dev-down dev-compose-up dev-compose-up-rebuild dev-compose-build dev-compose-down dev-compose-logs topics-create

# Default target
help: ## Show this help message
	@echo "Loom v2 Development Commands"
	@echo "============================"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development environment
setup: ## Set up development environment
	@echo "Setting up development environment..."
	@command -v tilt >/dev/null 2>&1 || { echo "Tilt not found. Install from https://docs.tilt.dev/install.html"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "Helm not found. Install from https://helm.sh/docs/intro/install/"; exit 1; }
	@command -v uv >/dev/null 2>&1 || { echo "uv not found. Install from https://docs.astral.sh/uv/"; exit 1; }
	@command -v pre-commit >/dev/null 2>&1 || pip install pre-commit
	@pre-commit install
	@echo "✅ Development environment ready"

dev-up: ## Start local development environment with Tilt
	@command -v tilt >/dev/null 2>&1 || { echo "Tilt not found. Install from https://tilt.dev/"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found. Install Kubernetes CLI"; exit 1; }
	tilt up

dev-down: ## Stop local development environment
	tilt down

dev-compose-up: ## Start local development environment with Docker Compose
	@echo "Starting Loom v2 services with Docker Compose..."
	docker compose -f docker-compose.local.yml up -d
	@echo "✅ Services started:"

dev-compose-up-rebuild: ## Start local development environment with Docker Compose (force rebuild)
	@echo "Rebuilding and starting Loom v2 services with Docker Compose..."
	docker compose -f docker-compose.local.yml up -d --build
	@echo "✅ Services rebuilt and started:"
	@echo "  Core Services:"
	@echo "    - Pipeline Monitor: http://localhost:3000"
	@echo "    - Pipeline Monitor API: http://localhost:8082"
	@echo "    - Ingestion API: http://localhost:8000"
	@echo "    - Kafka UI: http://localhost:8081"
	@echo "    - PostgreSQL: localhost:5432"
	@echo "    - Kafka: localhost:9092"
	@echo "  AI Services:"
	@echo "    - Silero VAD: http://localhost:8001"
	@echo "    - Parakeet TDT (STT): http://localhost:8002"
	@echo "    - MiniCPM Vision: http://localhost:8003"
	@echo "    - BUD-E Emotion: http://localhost:8004"
	@echo "    - Face Emotion: http://localhost:8005"
	@echo "  Data Fetchers:"
	@echo "    - HackerNews Fetcher (15min intervals)"
	@echo "    - Email Fetcher (5min intervals)"
	@echo "    - Calendar Fetcher (10min intervals)"
	@echo "    - X/Twitter Likes Fetcher (30min intervals)"
	@echo "  Processing Services:"
	@echo "    - HackerNews URL Processor"
	@echo "    - X/Twitter URL Processor"
	@echo "    - Kafka-to-DB Consumer"
	@echo "    - Scheduled Consumers Coordinator"

dev-compose-build: ## Build specific service(s) with Docker Compose (use SERVICE=<name>)
	@if [ -z "$(SERVICE)" ]; then \
		echo "Building all services..."; \
		docker compose -f docker-compose.local.yml build; \
	else \
		echo "Building service: $(SERVICE)..."; \
		docker compose -f docker-compose.local.yml build $(SERVICE); \
	fi
	@echo "✅ Build complete"

dev-compose-down: ## Stop Docker Compose environment
	@echo "Stopping Loom v2 services..."
	docker compose -f docker-compose.local.yml down

dev-compose-logs: ## View Docker Compose logs (use SERVICE=<name> for specific service)
	@if [ -z "$(SERVICE)" ]; then \
		docker compose -f docker-compose.local.yml logs -f; \
	else \
		docker compose -f docker-compose.local.yml logs -f $(SERVICE); \
	fi

# Testing
test: ## Run all tests
	@echo "Running ingestion-api tests..."
	@cd services/ingestion-api && make test

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	@cd services/ingestion-api && make test-coverage

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	@cd services/ingestion-api && make test-integration

test-e2e: ## Run end-to-end pipeline test
	@echo "Installing script dependencies..."
	@pip install -r scripts/requirements.txt
	@echo "Running end-to-end pipeline test..."
	@python3 scripts/e2e_test_pipeline.py

# Code quality
lint: ## Run linting on all services
	@echo "Running pre-commit hooks..."
	@pre-commit run --all-files

format: ## Format code
	@echo "Formatting code..."
	@find services/ -name "*.py" -exec black {} \;
	@find services/ -name "*.py" -exec ruff --fix {} \;

# Docker
docker: ## Build all Docker images
	@echo "Building ingestion-api image..."
	@cd services/ingestion-api && make docker
	@echo "Building pipeline-monitor-api image..."
	@cd services/pipeline-monitor-api && make docker
	@echo "Building pipeline-monitor image..."
	@cd services/pipeline-monitor && make docker

docker-push: ## Push Docker images to registry
	@echo "Pushing Docker images..."
	@cd services/ingestion-api && make docker-push

# Kafka management
topics-create: ## Create Kafka topics
	@echo "Creating Kafka topics..."
	@python scripts/create_kafka_topics.py --bootstrap-servers localhost:9092 --create-processed

topics-list: ## List Kafka topics
	@echo "Listing Kafka topics..."
	@kubectl exec -n loom-dev deployment/kafka -- kafka-topics.sh --bootstrap-server localhost:9092 --list

# Helm
helm-lint: ## Lint all Helm charts
	@echo "Linting Helm charts..."
	@helm lint deploy/helm/*/

helm-template: ## Template all Helm charts
	@echo "Templating Helm charts..."
	@for chart in deploy/helm/*/; do \
		echo "Templating $$chart"; \
		helm template test "$$chart" --dry-run; \
	done

# Cleanup
clean: ## Clean up build artifacts
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@rm -f bandit-report.json

# Database
db-connect: ## Connect to local PostgreSQL database
	@kubectl exec -n loom-dev -it deployment/postgres -- psql -U loom -d loom

# Monitoring
logs: ## Show logs for all services
	@kubectl logs -n loom-dev -l app.kubernetes.io/part-of=loom --tail=100 -f

status: ## Show status of all services
	@kubectl get pods -n loom-dev
	@echo ""
	@kubectl get services -n loom-dev

# Security
security-scan: ## Run security scans
	@echo "Running security scans..."
	@bandit -r services/ -f txt
	@safety check

# Documentation
docs-serve: ## Serve documentation locally
	@echo "Documentation commands not yet implemented"

# Release
release: ## Create a new release (requires VERSION env var)
	@if [ -z "$(VERSION)" ]; then echo "VERSION env var required"; exit 1; fi
	@echo "Creating release $(VERSION)..."
	@git tag -a v$(VERSION) -m "Release v$(VERSION)"
	@git push origin v$(VERSION)
