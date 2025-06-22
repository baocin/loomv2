#!/bin/bash
# Simple test script for ingestion API only (without Kafka dependencies)
# Idempotent and focused on quick API testing

set -e

# Configuration
API_PORT=8000
CONTAINER_NAME="loom-ingestion-api-test"
IMAGE_NAME="loom-ingestion-api:test"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Wait for health check
wait_for_health() {
    local max_attempts=30
    local attempt=1

    log_info "Waiting for health check..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:$API_PORT/healthz" > /dev/null 2>&1; then
            log_success "API is healthy!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "Health check failed after $max_attempts attempts"
    return 1
}

# Stop existing container
stop_container() {
    if docker ps -a -q -f name="$CONTAINER_NAME" | grep -q .; then
        log_info "Stopping existing container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}

# Build and run
main() {
    echo "🚀 Testing Ingestion API"
    echo "======================="

    # Stop existing
    stop_container

    # Build image
    log_info "Building Docker image..."
    cd services/ingestion-api
    docker build -t "$IMAGE_NAME" .
    cd ../..

    # Run container (without Kafka for quick testing)
    log_info "Starting container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p "$API_PORT:8000" \
        -e LOOM_LOG_LEVEL=DEBUG \
        -e LOOM_KAFKA_BOOTSTRAP_SERVERS=dummy:9092 \
        "$IMAGE_NAME"

    # Wait for health
    if wait_for_health; then
        log_success "Container is running!"

        # Show status
        echo ""
        echo "📊 Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "$CONTAINER_NAME"

        echo ""
        echo "🌐 URLs:"
        echo "  API: http://localhost:$API_PORT"
        echo "  Docs: http://localhost:$API_PORT/docs"
        echo "  Health: http://localhost:$API_PORT/healthz"

        echo ""
        echo "🧪 Quick Test:"
        curl -s "http://localhost:$API_PORT/healthz" | jq '.' 2>/dev/null || curl -s "http://localhost:$API_PORT/healthz"

        echo ""
        echo "📝 Commands:"
        echo "  docker logs -f $CONTAINER_NAME"
        echo "  docker stop $CONTAINER_NAME"

    else
        log_error "Container failed to start"
        echo "Logs:"
        docker logs "$CONTAINER_NAME"
        return 1
    fi
}

# Cleanup
if [[ "$1" == "cleanup" || "$1" == "clean" ]]; then
    stop_container
    docker rmi "$IMAGE_NAME" 2>/dev/null || true
    log_success "Cleaned up!"
    exit 0
fi

# Run main
main
