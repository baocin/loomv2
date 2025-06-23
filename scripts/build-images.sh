#!/bin/bash
# Build all Docker images for Loom v2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Building Docker images for Loom v2${NC}"
echo "========================================"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Function to build an image
build_image() {
    local service_name="$1"
    local service_path="$2"
    local image_tag="loom/${service_name}:latest"
    
    echo -e "\n${YELLOW}📦 Building ${service_name}...${NC}"
    
    if [ ! -d "$service_path" ]; then
        echo -e "${RED}❌ Service directory not found: $service_path${NC}"
        return 1
    fi
    
    cd "$service_path"
    
    if [ ! -f "Dockerfile" ]; then
        echo -e "${RED}❌ Dockerfile not found in $service_path${NC}"
        return 1
    fi
    
    # Build the image
    docker build -t "$image_tag" .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Successfully built $image_tag${NC}"
    else
        echo -e "${RED}❌ Failed to build $image_tag${NC}"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

# Build ingestion-api
build_image "ingestion-api" "services/ingestion-api"

# Build vad-processor
build_image "vad-processor" "services/vad-processor"

# List built images
echo -e "\n${BLUE}📋 Built images:${NC}"
docker images | grep "loom/" | head -10

echo -e "\n${GREEN}🎉 All images built successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Start k3s cluster: ./scripts/deploy-k3s.sh"
echo "  2. Deploy services: kubectl apply -f deploy/k3s/loom-complete.yaml"
echo "  3. Test deployment: ./scripts/test-deployment.sh"