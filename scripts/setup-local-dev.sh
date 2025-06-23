#!/bin/bash
# Complete setup script for Loom v2 local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🚀 Loom v2 Local Development Setup${NC}"
echo "=================================="
echo ""
echo "This script will:"
echo "  1. Check and install dependencies"
echo "  2. Build Docker images"
echo "  3. Create k3s cluster"
echo "  4. Deploy all services"
echo "  5. Run deployment tests"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install k3d
install_k3d() {
    echo -e "${YELLOW}📦 Installing k3d...${NC}"
    if curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash; then
        echo -e "${GREEN}✅ k3d installed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to install k3d${NC}"
        exit 1
    fi
}

# Function to install kubectl
install_kubectl() {
    echo -e "${YELLOW}📦 Installing kubectl...${NC}"
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
        chmod +x kubectl
        sudo mv kubectl /usr/local/bin/
    else
        echo -e "${RED}❌ Unsupported OS. Please install kubectl manually.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ kubectl installed successfully${NC}"
}

# Step 1: Check dependencies
echo -e "${BLUE}📋 Checking dependencies...${NC}"

# Check Docker
if command_exists docker; then
    echo -e "${GREEN}✅ Docker is installed${NC}"
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check k3d
if command_exists k3d; then
    echo -e "${GREEN}✅ k3d is installed${NC}"
else
    echo -e "${YELLOW}⚠️  k3d is not installed${NC}"
    read -p "Install k3d? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_k3d
    else
        echo -e "${RED}❌ k3d is required. Exiting.${NC}"
        exit 1
    fi
fi

# Check kubectl
if command_exists kubectl; then
    echo -e "${GREEN}✅ kubectl is installed${NC}"
else
    echo -e "${YELLOW}⚠️  kubectl is not installed${NC}"
    read -p "Install kubectl? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_kubectl
    else
        echo -e "${RED}❌ kubectl is required. Exiting.${NC}"
        exit 1
    fi
fi

# Check Python and uv
if command_exists python3; then
    echo -e "${GREEN}✅ Python 3 is installed${NC}"
else
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.11+ first.${NC}"
    exit 1
fi

if command_exists uv; then
    echo -e "${GREEN}✅ uv is installed${NC}"
else
    echo -e "${YELLOW}⚠️  uv is not installed. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Step 2: Build Docker images
echo -e "\n${BLUE}🏗️  Building Docker images...${NC}"
cd "$PROJECT_ROOT"
chmod +x scripts/build-images.sh
./scripts/build-images.sh

# Step 3: Deploy to k3s
echo -e "\n${BLUE}🚀 Deploying to k3s...${NC}"
chmod +x scripts/deploy-k3s.sh
./scripts/deploy-k3s.sh

# Step 4: Run tests
echo -e "\n${BLUE}🧪 Running deployment tests...${NC}"
chmod +x scripts/test-deployment.sh
sleep 10  # Give services time to fully start
./scripts/test-deployment.sh

# Final summary
echo -e "\n${GREEN}🎉 Loom v2 setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}🌟 What's running:${NC}"
echo "  • k3s Kubernetes cluster: loom-local"
echo "  • TimescaleDB with hypertables and compression"
echo "  • Kafka with auto-topic creation"
echo "  • Ingestion API with health checks"
echo "  • Kafka UI for monitoring"
echo "  • Database migrations applied"
echo "  • Test data generator (runs every 2 minutes)"
echo ""
echo -e "${BLUE}🔗 Quick access:${NC}"
echo "  • API:        http://localhost:30000"
echo "  • API Docs:   http://localhost:30000/docs"
echo "  • Kafka UI:   http://localhost:30081"
echo "  • Database:   localhost:30432 (loom/loom)"
echo "  • Kafka:      localhost:30092"
echo ""
echo -e "${BLUE}📝 Useful commands:${NC}"
echo "  • Check status:   kubectl get pods -n loom"
echo "  • View logs:      kubectl logs -f deployment/ingestion-api -n loom"
echo "  • Test API:       curl http://localhost:30000/healthz"
echo "  • Cleanup:        k3d cluster delete loom-local"
echo ""
echo -e "${BLUE}📚 Next steps:${NC}"
echo "  1. Open API docs: http://localhost:30000/docs"
echo "  2. Try the sensor endpoints to send test data"
echo "  3. Monitor Kafka topics: http://localhost:30081"
echo "  4. View TimescaleDB data with any PostgreSQL client"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"