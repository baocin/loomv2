#!/bin/bash
# Run tests for all Loom v2 services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICES_DIR="$PROJECT_ROOT/services"

echo "======================================"
echo "Running tests for all Loom v2 services"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
declare -A test_results
failed_services=()

# Function to run tests for a service
run_service_tests() {
    local service_name=$1
    local service_path="$SERVICES_DIR/$service_name"
    
    if [ ! -d "$service_path" ]; then
        echo -e "${YELLOW}⚠ Skipping $service_name (directory not found)${NC}"
        return
    fi
    
    if [ ! -d "$service_path/tests" ]; then
        echo -e "${YELLOW}⚠ Skipping $service_name (no tests directory)${NC}"
        test_results[$service_name]="NO_TESTS"
        return
    fi
    
    echo -e "\n${GREEN}Testing $service_name...${NC}"
    echo "----------------------------------------"
    
    cd "$service_path"
    
    # Check if there are any test files
    if ! find tests -name "test_*.py" -type f | grep -q .; then
        echo -e "${YELLOW}No test files found${NC}"
        test_results[$service_name]="NO_TEST_FILES"
        return
    fi
    
    # Install test dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies..."
        pip install -q -r requirements.txt 2>/dev/null || true
    fi
    
    # Install pytest if not already installed
    pip install -q pytest pytest-asyncio pytest-cov 2>/dev/null || true
    
    # Run tests
    if python -m pytest tests/ -v --tb=short; then
        echo -e "${GREEN}✓ Tests passed${NC}"
        test_results[$service_name]="PASSED"
    else
        echo -e "${RED}✗ Tests failed${NC}"
        test_results[$service_name]="FAILED"
        failed_services+=("$service_name")
    fi
}

# List of services to test
services=(
    "kafka-to-db-consumer"
    "email-fetcher"
    "calendar-fetcher"
    "x-likes-fetcher"
    "hackernews-fetcher"
    "ingestion-api"
    "pipeline-monitor"
    "kafka-test-producer"
    "silero-vad"
    "parakeet-tdt"
    "minicpm-vision"
    "mistral-reasoning"
    "moondream-ocr"
    "text-embedder"
)

# Run tests for each service
for service in "${services[@]}"; do
    run_service_tests "$service"
done

# Print summary
echo -e "\n\n======================================"
echo "Test Summary"
echo "======================================"

for service in "${services[@]}"; do
    result="${test_results[$service]:-NOT_RUN}"
    case $result in
        PASSED)
            echo -e "${GREEN}✓ $service: PASSED${NC}"
            ;;
        FAILED)
            echo -e "${RED}✗ $service: FAILED${NC}"
            ;;
        NO_TESTS)
            echo -e "${YELLOW}⚠ $service: No tests directory${NC}"
            ;;
        NO_TEST_FILES)
            echo -e "${YELLOW}⚠ $service: No test files${NC}"
            ;;
        *)
            echo -e "${YELLOW}? $service: Not run${NC}"
            ;;
    esac
done

# Exit with error if any tests failed
if [ ${#failed_services[@]} -gt 0 ]; then
    echo -e "\n${RED}Failed services: ${failed_services[*]}${NC}"
    exit 1
else
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
fi