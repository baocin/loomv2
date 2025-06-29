.PHONY: help setup test lint format docker clean dev-up dev-down dev-compose-up dev-compose-up-rebuild dev-compose-build dev-compose-down dev-compose-logs topics-create base-images

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
	./scripts/docker-build-with-labels.sh
	docker compose -f docker-compose.local.yml up -d
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
		echo "Building all services with git labels..."; \
		./scripts/docker-build-with-labels.sh; \
	else \
		echo "Building service: $(SERVICE) with git labels..."; \
		export GIT_COMMIT=$$(git rev-parse HEAD 2>/dev/null || echo "unknown"); \
		export GIT_BRANCH=$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown"); \
		export BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ"); \
		export BUILD_VERSION=$$(git describe --tags --always 2>/dev/null || echo "latest"); \
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
base-images: ## Build base Docker images for all services
	@echo "Building base Docker images..."
	@cd docker/base-images && ./build.sh
	@echo "✅ Base images built successfully"

docker: base-images ## Build all Docker images
	@echo "Building ingestion-api image..."
	@cd services/ingestion-api && make docker
	@echo "Building pipeline-monitor-api image..."
	@cd services/pipeline-monitor-api && make docker
	@echo "Building pipeline-monitor image..."
	@cd services/pipeline-monitor && make docker

docker-push: ## Push Docker images to registry
	@echo "Pushing Docker images..."
	@cd services/ingestion-api && make docker-push

docker-labels: ## Show git labels for Docker images (use SERVICE=<name> for specific service)
	@if [ -z "$(SERVICE)" ]; then \
		echo "Showing labels for all loom images:"; \
		for image in $$(docker images --format "{{.Repository}}" | grep -E "^loom-|loomv2" | sort -u); do \
			echo ""; \
			echo "=== $$image ==="; \
			docker inspect "$$image:latest" --format '{{json .Config.Labels}}' 2>/dev/null | jq . || echo "Image not found"; \
		done; \
	else \
		echo "Showing labels for $(SERVICE):"; \
		docker inspect "loomv2-$(SERVICE):latest" --format '{{json .Config.Labels}}' | jq . || \
		docker inspect "$(SERVICE):latest" --format '{{json .Config.Labels}}' | jq .; \
	fi

# Kafka management
topics-create: ## Create Kafka topics
	@echo "Creating Kafka topics..."
	@python3 scripts/create_kafka_topics.py --bootstrap-servers localhost:9092 --create-processed

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

clean-all: ## Complete cleanup - DESTRUCTIVE! Removes all data, topics, and consumer groups
	@echo "⚠️  WARNING: This will delete ALL data including:"
	@echo "  - PostgreSQL/TimescaleDB data"
	@echo "  - All Kafka topics and consumer groups"
	@echo "  - All Zookeeper data"
	@echo ""
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	@echo ""
	@echo "Stopping all services..."
	@docker compose -f docker-compose.local.yml down -v || true
	@echo ""
	@echo "Removing persistent volumes..."
	@rm -rf ~/.loom/timescaledb ~/.loom/kafka ~/.loom/zookeeper ~/.loom/models 2>/dev/null || true
	@echo ""
	@echo "Removing any orphaned Docker volumes..."
	@docker volume prune -f 2>/dev/null || true
	@echo ""
	@echo "✅ Complete cleanup done. All data has been removed."
	@echo "Run 'make dev-compose-up' to start fresh."

clean-kafka: ## Clean all Kafka topics and consumer groups (keeps database)
	@echo "⚠️  WARNING: This will delete all Kafka topics and consumer groups"
	@echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
	@sleep 3
	@echo ""
	@echo "Deleting all consumer groups..."
	@docker exec loomv2-kafka-1 bash -c 'kafka-consumer-groups --bootstrap-server localhost:9092 --list | xargs -P 10 -I {} kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group {} 2>/dev/null' || true
	@echo ""
	@echo "Deleting all topics except __consumer_offsets..."
	@docker exec loomv2-kafka-1 bash -c 'kafka-topics --bootstrap-server localhost:9092 --list | grep -v "^__consumer_offsets$$" | xargs -P 10 -I {} kafka-topics --bootstrap-server localhost:9092 --delete --topic {} 2>/dev/null' || true
	@echo ""
	@echo "Waiting for deletions to propagate..."
	@sleep 5
	@echo ""
	@echo "Recreating topics..."
	@python3 scripts/create_kafka_topics.py --bootstrap-servers localhost:9092 --create-processed || true
	@echo ""
	@echo "✅ Kafka cleanup complete. Topics recreated."

clean-db: ## Clean database only (keeps Kafka)
	@echo "⚠️  WARNING: This will delete all PostgreSQL/TimescaleDB data"
	@echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
	@sleep 3
	@echo ""
	@echo "Stopping database container..."
	@docker compose -f docker-compose.local.yml stop postgres
	@echo ""
	@echo "Removing database volume..."
	@rm -rf ~/.loom/timescaledb 2>/dev/null || true
	@echo ""
	@echo "Starting database container..."
	@docker compose -f docker-compose.local.yml up -d postgres
	@echo ""
	@echo "Waiting for database to be ready..."
	@sleep 10
	@echo ""
	@echo "✅ Database cleanup complete. Fresh database ready."

clean-monitor-consumers: ## Clean up orphaned monitor consumer groups
	@echo "Cleaning up monitor consumer groups..."
	@./scripts/cleanup_monitor_consumer_groups_batch.sh

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
