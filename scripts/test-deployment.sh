#!/bin/bash
# Test Loom v2 deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing Loom v2 Deployment${NC}"
echo "=============================="

# Test configuration
API_URL="http://localhost:30000"
KAFKA_UI_URL="http://localhost:30081"
TIMEOUT=10

# Function to test endpoint
test_endpoint() {
    local url="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    echo -e "${YELLOW}🔍 Testing: $description${NC}"
    echo "   URL: $url"
    
    if response=$(curl -s -w "%{http_code}" -o /tmp/response.txt --connect-timeout $TIMEOUT "$url"); then
        status_code="${response: -3}"
        
        if [ "$status_code" = "$expected_status" ]; then
            echo -e "${GREEN}   ✅ Success (HTTP $status_code)${NC}"
            return 0
        else
            echo -e "${RED}   ❌ Failed (HTTP $status_code, expected $expected_status)${NC}"
            echo "   Response: $(cat /tmp/response.txt)"
            return 1
        fi
    else
        echo -e "${RED}   ❌ Connection failed${NC}"
        return 1
    fi
}

# Function to test API endpoints
test_api_endpoints() {
    echo -e "\n${BLUE}🔗 Testing API Endpoints${NC}"
    echo "------------------------"
    
    # Health check
    test_endpoint "$API_URL/healthz" 200 "Health check endpoint"
    
    # Readiness check
    test_endpoint "$API_URL/readyz" 200 "Readiness check endpoint"
    
    # API documentation
    test_endpoint "$API_URL/docs" 200 "API documentation"
    
    # OpenAPI spec
    test_endpoint "$API_URL/openapi.json" 200 "OpenAPI specification"
    
    # Metrics endpoint
    test_endpoint "$API_URL/metrics" 200 "Prometheus metrics"
    
    echo -e "${GREEN}✅ All API endpoints are responding${NC}"
}

# Function to test data ingestion
test_data_ingestion() {
    echo -e "\n${BLUE}📊 Testing Data Ingestion${NC}"
    echo "-------------------------"
    
    # Test GPS sensor data ingestion
    echo -e "${YELLOW}🌍 Testing GPS sensor ingestion...${NC}"
    
    gps_data='{
        "device_id": "test-device-001",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.5,
        "accuracy": 5.0,
        "speed": 0.0
    }'
    
    if response=$(curl -s -w "%{http_code}" -o /tmp/gps_response.txt \
        --connect-timeout $TIMEOUT \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$gps_data" \
        "$API_URL/sensor/gps"); then
        
        status_code="${response: -3}"
        
        if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
            echo -e "${GREEN}   ✅ GPS data ingestion successful (HTTP $status_code)${NC}"
        else
            echo -e "${YELLOW}   ⚠️  GPS data ingestion returned HTTP $status_code${NC}"
            echo "   Response: $(cat /tmp/gps_response.txt)"
        fi
    else
        echo -e "${RED}   ❌ GPS data ingestion failed${NC}"
    fi
    
    # Test heartrate data ingestion
    echo -e "${YELLOW}❤️  Testing heartrate sensor ingestion...${NC}"
    
    hr_data='{
        "device_id": "test-device-001",
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "heart_rate": 72,
        "confidence": 0.95
    }'
    
    if response=$(curl -s -w "%{http_code}" -o /tmp/hr_response.txt \
        --connect-timeout $TIMEOUT \
        -H "Content-Type: application/json" \
        -X POST \
        -d "$hr_data" \
        "$API_URL/sensor/heartrate"); then
        
        status_code="${response: -3}"
        
        if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
            echo -e "${GREEN}   ✅ Heartrate data ingestion successful (HTTP $status_code)${NC}"
        else
            echo -e "${YELLOW}   ⚠️  Heartrate data ingestion returned HTTP $status_code${NC}"
            echo "   Response: $(cat /tmp/hr_response.txt)"
        fi
    else
        echo -e "${RED}   ❌ Heartrate data ingestion failed${NC}"
    fi
}

# Function to test Kafka UI
test_kafka_ui() {
    echo -e "\n${BLUE}📡 Testing Kafka UI${NC}"
    echo "------------------"
    
    if test_endpoint "$KAFKA_UI_URL" 200 "Kafka UI interface"; then
        echo -e "${GREEN}✅ Kafka UI is accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Kafka UI may not be ready yet${NC}"
    fi
}

# Function to check cluster status
check_cluster_status() {
    echo -e "\n${BLUE}🏥 Cluster Health Check${NC}"
    echo "----------------------"
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl not found${NC}"
        return 1
    fi
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Kubernetes cluster is accessible${NC}"
    
    # Check pod status
    echo -e "\n${YELLOW}📋 Pod Status:${NC}"
    kubectl get pods -n loom -o wide | grep -v "Completed"
    
    # Check failed pods
    failed_pods=$(kubectl get pods -n loom --field-selector=status.phase=Failed -o name 2>/dev/null | wc -l)
    if [ "$failed_pods" -gt 0 ]; then
        echo -e "${RED}⚠️  Found $failed_pods failed pod(s)${NC}"
        kubectl get pods -n loom --field-selector=status.phase=Failed
    fi
    
    # Check service status
    echo -e "\n${YELLOW}🌐 Service Status:${NC}"
    kubectl get services -n loom
    
    # Check TimescaleDB status
    echo -e "\n${YELLOW}🗄️  TimescaleDB Status:${NC}"
    if kubectl get pod -l app=timescaledb -n loom -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q "Running"; then
        echo -e "${GREEN}✅ TimescaleDB is running${NC}"
    else
        echo -e "${RED}❌ TimescaleDB is not running${NC}"
    fi
    
    # Check Kafka status
    echo -e "\n${YELLOW}📡 Kafka Status:${NC}"
    if kubectl get pod -l app=kafka -n loom -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q "Running"; then
        echo -e "${GREEN}✅ Kafka is running${NC}"
    else
        echo -e "${RED}❌ Kafka is not running${NC}"
    fi
}

# Function to test database connectivity
test_database() {
    echo -e "\n${BLUE}🗄️  Testing Database Connectivity${NC}"
    echo "--------------------------------"
    
    # Try to connect to TimescaleDB
    if kubectl exec -n loom deployment/timescaledb -- psql -U loom -d loom -c "SELECT version();" &> /dev/null; then
        echo -e "${GREEN}✅ TimescaleDB connection successful${NC}"
        
        # Check TimescaleDB extension
        if kubectl exec -n loom deployment/timescaledb -- psql -U loom -d loom -c "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';" | grep -q timescaledb; then
            echo -e "${GREEN}✅ TimescaleDB extension is installed${NC}"
        else
            echo -e "${YELLOW}⚠️  TimescaleDB extension not found${NC}"
        fi
        
        # Check for hypertables
        table_count=$(kubectl exec -n loom deployment/timescaledb -- psql -U loom -d loom -t -c "SELECT COUNT(*) FROM timescaledb_information.hypertables;" 2>/dev/null | tr -d ' ')
        if [ "$table_count" -gt 0 ]; then
            echo -e "${GREEN}✅ Found $table_count hypertable(s)${NC}"
        else
            echo -e "${YELLOW}⚠️  No hypertables found (migration may not have run)${NC}"
        fi
        
    else
        echo -e "${RED}❌ Cannot connect to TimescaleDB${NC}"
    fi
}

# Function to test Kafka connectivity
test_kafka() {
    echo -e "\n${BLUE}📡 Testing Kafka Connectivity${NC}"
    echo "----------------------------"
    
    # Try to list Kafka topics
    if kubectl exec -n loom deployment/kafka -- kafka-topics.sh --list --bootstrap-server localhost:9092 &> /dev/null; then
        echo -e "${GREEN}✅ Kafka connection successful${NC}"
        
        # Count topics
        topic_count=$(kubectl exec -n loom deployment/kafka -- kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ Found $topic_count Kafka topic(s)${NC}"
        
        # List some topics
        echo -e "${YELLOW}📋 Available topics:${NC}"
        kubectl exec -n loom deployment/kafka -- kafka-topics.sh --list --bootstrap-server localhost:9092 2>/dev/null | head -10
        
    else
        echo -e "${RED}❌ Cannot connect to Kafka${NC}"
    fi
}

# Main test execution
main() {
    echo -e "${BLUE}Starting comprehensive deployment test...${NC}"
    
    # Check cluster status first
    check_cluster_status
    
    # Test API endpoints
    test_api_endpoints
    
    # Test data ingestion
    test_data_ingestion
    
    # Test Kafka UI
    test_kafka_ui
    
    # Test database
    test_database
    
    # Test Kafka
    test_kafka
    
    # Summary
    echo -e "\n${GREEN}🎉 Deployment test completed!${NC}"
    echo ""
    echo -e "${BLUE}📊 Summary:${NC}"
    echo "  🔗 API available at:     $API_URL"
    echo "  📚 API docs at:         $API_URL/docs"
    echo "  📡 Kafka UI at:         $KAFKA_UI_URL"
    echo "  🗄️  Database at:         localhost:30432"
    echo "  📊 Kafka at:            localhost:30092"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "  • View API docs: open $API_URL/docs"
    echo "  • Monitor Kafka: open $KAFKA_UI_URL"
    echo "  • Send test data: curl -X POST $API_URL/sensor/gps -H 'Content-Type: application/json' -d '{...}'"
    echo "  • View logs: kubectl logs -f deployment/ingestion-api -n loom"
    
    # Cleanup temp files
    rm -f /tmp/response.txt /tmp/gps_response.txt /tmp/hr_response.txt
}

# Run main function
main "$@"