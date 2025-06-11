#!/bin/bash
# Test script to build and run Docker containers locally
# Idempotent - can be run multiple times safely

set -e

# Configuration
INGESTION_API_PORT=8000
KAFKA_PORT=9092
ZOOKEEPER_PORT=2181
NETWORK_NAME="loom-test-network"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for service to be healthy
wait_for_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    log_info "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            log_success "$service_name is healthy!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "$service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Stop and remove container if exists
stop_and_remove() {
    local container_name=$1
    
    if docker ps -a --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        log_info "Stopping and removing existing container: $container_name"
        docker stop "$container_name" >/dev/null 2>&1 || true
        docker rm "$container_name" >/dev/null 2>&1 || true
    fi
}

# Create Docker network if it doesn't exist
create_network() {
    if ! docker network ls --format "table {{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        log_info "Creating Docker network: $NETWORK_NAME"
        docker network create "$NETWORK_NAME"
    else
        log_info "Docker network $NETWORK_NAME already exists"
    fi
}

# Test Zookeeper
test_zookeeper() {
    log_info "🐘 Testing Zookeeper..."
    
    stop_and_remove "loom-zookeeper-test"
    
    log_info "Starting Zookeeper container..."
    docker run -d \
        --name loom-zookeeper-test \
        --network "$NETWORK_NAME" \
        -p $ZOOKEEPER_PORT:2181 \
        -e ZOOKEEPER_CLIENT_PORT=2181 \
        -e ZOOKEEPER_TICK_TIME=2000 \
        confluentinc/cp-zookeeper:7.4.0
    
    # Wait for Zookeeper to be ready (no HTTP endpoint, so just wait)
    log_info "Waiting for Zookeeper to start..."
    sleep 10
    
    # Test Zookeeper connection
    if docker exec loom-zookeeper-test zkServer.sh status; then
        log_success "Zookeeper is running successfully!"
    else
        log_error "Zookeeper failed to start properly"
        return 1
    fi
}

# Test Kafka
test_kafka() {
    log_info "📨 Testing Kafka..."
    
    stop_and_remove "loom-kafka-test"
    
    log_info "Starting Kafka container..."
    docker run -d \
        --name loom-kafka-test \
        --network "$NETWORK_NAME" \
        -p $KAFKA_PORT:9092 \
        -e KAFKA_BROKER_ID=1 \
        -e KAFKA_ZOOKEEPER_CONNECT=loom-zookeeper-test:2181 \
        -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
        -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
        -e KAFKA_AUTO_CREATE_TOPICS_ENABLE=true \
        confluentinc/cp-kafka:7.4.0
    
    # Wait for Kafka to be ready
    log_info "Waiting for Kafka to start..."
    sleep 20
    
    # Test Kafka by creating a topic
    if docker exec loom-kafka-test kafka-topics --create --topic test-topic --bootstrap-server localhost:9092 --replication-factor 1 --partitions 1; then
        log_success "Kafka is running successfully!"
        
        # List topics to verify
        log_info "Available Kafka topics:"
        docker exec loom-kafka-test kafka-topics --list --bootstrap-server localhost:9092
    else
        log_error "Kafka failed to start properly"
        return 1
    fi
}

# Test Ingestion API
test_ingestion_api() {
    log_info "🚀 Testing Ingestion API..."
    
    stop_and_remove "loom-ingestion-api-test"
    
    # Build the image
    log_info "Building ingestion-api Docker image..."
    cd services/ingestion-api
    docker build -t loom-ingestion-api:test .
    cd ../..
    
    # Run the container
    log_info "Starting ingestion-api container..."
    docker run -d \
        --name loom-ingestion-api-test \
        --network "$NETWORK_NAME" \
        -p $INGESTION_API_PORT:8000 \
        -e LOOM_KAFKA_BOOTSTRAP_SERVERS=loom-kafka-test:9092 \
        -e LOOM_LOG_LEVEL=DEBUG \
        loom-ingestion-api:test
    
    # Wait for health check to pass
    if wait_for_health "Ingestion API" "http://localhost:$INGESTION_API_PORT/healthz" 30; then
        log_success "Ingestion API is running successfully!"
        
        # Test basic endpoints
        log_info "Testing API endpoints..."
        
        echo "Root endpoint:"
        curl -s "http://localhost:$INGESTION_API_PORT/" | jq '.' || curl -s "http://localhost:$INGESTION_API_PORT/"
        
        echo -e "\nHealth check:"
        curl -s "http://localhost:$INGESTION_API_PORT/healthz" | jq '.' || curl -s "http://localhost:$INGESTION_API_PORT/healthz"
        
        echo -e "\nReadiness check:"
        curl -s "http://localhost:$INGESTION_API_PORT/readyz" | jq '.' || curl -s "http://localhost:$INGESTION_API_PORT/readyz"
        
    else
        log_error "Ingestion API failed to start properly"
        log_info "Container logs:"
        docker logs loom-ingestion-api-test
        return 1
    fi
}

# Test full stack integration
test_integration() {
    log_info "🧪 Running integration tests..."
    
    # Test sensor endpoint
    log_info "Testing sensor endpoint..."
    sensor_response=$(curl -s -X POST "http://localhost:$INGESTION_API_PORT/sensor/gps" \
        -H "Content-Type: application/json" \
        -d '{
            "device_id": "test-device-123",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "accuracy": 5.0
        }')
    
    if echo "$sensor_response" | grep -q "success"; then
        log_success "Sensor endpoint test passed!"
        echo "Response: $sensor_response"
    else
        log_error "Sensor endpoint test failed!"
        echo "Response: $sensor_response"
    fi
    
    # Test audio upload endpoint
    log_info "Testing audio upload endpoint..."
    audio_response=$(curl -s -X POST "http://localhost:$INGESTION_API_PORT/audio/upload" \
        -H "Content-Type: application/json" \
        -d '{
            "device_id": "test-device-123",
            "chunk_data": "dGVzdCBhdWRpbyBkYXRh",
            "sample_rate": 44100,
            "duration_ms": 1000,
            "format": "wav"
        }')
    
    if echo "$audio_response" | grep -q "success"; then
        log_success "Audio upload endpoint test passed!"
        echo "Response: $audio_response"
    else
        log_error "Audio upload endpoint test failed!"
        echo "Response: $audio_response"
    fi
    
    # Verify Kafka topics were created
    log_info "Checking Kafka topics..."
    docker exec loom-kafka-test kafka-topics --list --bootstrap-server localhost:9092
}

# Show running services
show_status() {
    echo ""
    log_info "🔍 Service Status:"
    echo ""
    
    echo "Docker Containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep loom-.*-test || echo "No test containers running"
    
    echo ""
    echo "Service URLs:"
    echo "  🚀 Ingestion API: http://localhost:$INGESTION_API_PORT"
    echo "  📖 API Docs: http://localhost:$INGESTION_API_PORT/docs"
    echo "  ❤️ Health Check: http://localhost:$INGESTION_API_PORT/healthz"
    echo "  📨 Kafka: localhost:$KAFKA_PORT"
    echo ""
    
    echo "Useful Commands:"
    echo "  # View logs"
    echo "  docker logs -f loom-ingestion-api-test"
    echo "  docker logs -f loom-kafka-test"
    echo ""
    echo "  # Test WebSocket"
    echo "  wscat -c ws://localhost:$INGESTION_API_PORT/audio/stream/test-device"
    echo ""
    echo "  # Stop all test containers"
    echo "  docker stop loom-ingestion-api-test loom-kafka-test loom-zookeeper-test"
    echo ""
}

# Cleanup function
cleanup() {
    log_info "🧹 Cleaning up test containers..."
    stop_and_remove "loom-ingestion-api-test"
    stop_and_remove "loom-kafka-test" 
    stop_and_remove "loom-zookeeper-test"
    
    if docker network ls --format "table {{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        docker network rm "$NETWORK_NAME" 2>/dev/null || true
    fi
    
    log_success "Cleanup complete!"
}

# Main execution
main() {
    local command=${1:-"all"}
    
    case $command in
        "ingestion-api"|"api")
            create_network
            test_ingestion_api
            show_status
            ;;
        "kafka")
            create_network
            test_zookeeper
            test_kafka
            ;;
        "integration"|"test")
            test_integration
            ;;
        "cleanup"|"clean")
            cleanup
            exit 0
            ;;
        "status")
            show_status
            ;;
        "all"|*)
            create_network
            test_zookeeper
            test_kafka
            test_ingestion_api
            test_integration
            show_status
            ;;
    esac
}

# Handle script arguments
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "🐳 Loom Docker Test Script"
    echo "=========================="
    echo ""
    
    # Check dependencies
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed or not in PATH"
        exit 1
    fi
    
    main "$@"
fi 