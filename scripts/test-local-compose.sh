#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Running Loom v2 Integration Tests (Docker Compose)${NC}"

# Check if services are running
if ! curl -s http://localhost:8000/healthz >/dev/null; then
    echo -e "${RED}❌ Services not running. Run ./scripts/run-local-compose.sh first.${NC}"
    exit 1
fi

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected="$3"
    local method="${4:-GET}"
    
    echo -n "Testing $name... "
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' "$url" || echo "ERROR")
    else
        response=$(curl -s "$url" || echo "ERROR")
    fi
    
    if echo "$response" | grep -q "$expected"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC} (got: $response)"
        ((FAILED++))
    fi
}

# Test health endpoints
test_endpoint "Health check" "http://localhost:8000/healthz" "healthy"
test_endpoint "Readiness check" "http://localhost:8000/readyz" "ready"
test_endpoint "Metrics endpoint" "http://localhost:8000/metrics" "http_requests_total"

# Test API endpoints with minimal data
echo -n "Testing audio upload endpoint... "
response=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{
        "device_id": "test-device",
        "timestamp": "2024-01-01T00:00:00Z",
        "audio_data": "dGVzdA==",
        "sample_rate": 44100,
        "channels": 1,
        "format": "wav"
    }' http://localhost:8000/audio/upload || echo "ERROR")

if echo "$response" | grep -q "success\|accepted\|ok"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} (got: $response)"
    ((FAILED++))
fi

# Test sensor endpoints
echo -n "Testing GPS sensor endpoint... "
response=$(curl -s -X POST -H "Content-Type: application/json" \
    -d '{
        "device_id": "test-device",
        "timestamp": "2024-01-01T00:00:00Z",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "accuracy": 5.0
    }' http://localhost:8000/sensor/gps || echo "ERROR")

if echo "$response" | grep -q "success\|accepted\|ok"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} (got: $response)"
    ((FAILED++))
fi

# Test database connectivity
echo -n "Testing database connection... "
if docker exec $(docker ps -q -f name=postgres) psql -U loom -d loom -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';" >/dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Test Kafka connectivity
echo -n "Testing Kafka topic creation... "
if docker exec $(docker ps -q -f name=kafka) kafka-topics --bootstrap-server localhost:9092 --list | grep -q "device\|loom"; then
    echo -e "${GREEN}PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC}"
    ((FAILED++))
fi

# Run unit tests
echo -e "\n${YELLOW}Running unit tests...${NC}"
cd /home/aoi/code/loomv2/services/ingestion-api
if python -m pytest tests/ -v --tb=short; then
    echo -e "${GREEN}Unit tests: PASS${NC}"
    ((PASSED++))
else
    echo -e "${RED}Unit tests: FAIL${NC}"
    ((FAILED++))
fi

# Summary
echo ""
echo -e "${BLUE}📊 Test Summary:${NC}"
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed.${NC}"
    exit 1
fi