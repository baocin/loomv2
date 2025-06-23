#!/bin/bash
# Deploy Loom v2 to k3s cluster

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="loom-local"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}🚀 Deploying Loom v2 to k3s${NC}"
echo "=============================="

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
    echo -e "${RED}❌ k3d is not installed${NC}"
    echo "Install k3d: curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}❌ kubectl is not installed${NC}"
    echo "Install kubectl: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Function to wait for deployment
wait_for_deployment() {
    local namespace="$1"
    local deployment="$2"
    local timeout="${3:-300}"

    echo -e "${YELLOW}⏳ Waiting for deployment ${deployment} in namespace ${namespace}...${NC}"

    if kubectl wait --for=condition=available deployment/"$deployment" -n "$namespace" --timeout="${timeout}s"; then
        echo -e "${GREEN}✅ Deployment ${deployment} is ready${NC}"
        return 0
    else
        echo -e "${RED}❌ Deployment ${deployment} failed to become ready${NC}"
        return 1
    fi
}

# Function to wait for job completion
wait_for_job() {
    local namespace="$1"
    local job="$2"
    local timeout="${3:-300}"

    echo -e "${YELLOW}⏳ Waiting for job ${job} in namespace ${namespace}...${NC}"

    if kubectl wait --for=condition=complete job/"$job" -n "$namespace" --timeout="${timeout}s"; then
        echo -e "${GREEN}✅ Job ${job} completed successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Job ${job} failed or timed out${NC}"
        kubectl logs job/"$job" -n "$namespace" || true
        return 1
    fi
}

# Check if cluster exists
if k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo -e "${YELLOW}🔄 Cluster $CLUSTER_NAME already exists${NC}"
else
    echo -e "${YELLOW}🏗️  Creating k3s cluster: $CLUSTER_NAME${NC}"

    # Create k3s cluster with port mappings
    k3d cluster create "$CLUSTER_NAME" \
        --api-port 6443 \
        --port "30000:30000@loadbalancer" \
        --port "30081:30081@loadbalancer" \
        --port "30092:30092@loadbalancer" \
        --port "30432:30432@loadbalancer" \
        --agents 1 \
        --wait
fi

# Set kubectl context
kubectl config use-context "k3d-$CLUSTER_NAME"

# Import Docker images to k3s
echo -e "${YELLOW}📦 Importing Docker images to k3s...${NC}"
k3d image import loom/ingestion-api:latest -c "$CLUSTER_NAME" || echo "Image may not exist yet"
k3d image import loom/vad-processor:latest -c "$CLUSTER_NAME" || echo "Image may not exist yet"

# Deploy the application
echo -e "${YELLOW}🚀 Deploying Loom v2 services...${NC}"
kubectl apply -f "$PROJECT_ROOT/deploy/k3s/loom-complete.yaml"

# Wait for namespace
echo -e "${YELLOW}⏳ Waiting for namespace...${NC}"
kubectl wait --for=condition=Ready namespace/loom --timeout=30s

# Wait for core infrastructure
echo -e "\n${BLUE}📊 Waiting for core infrastructure...${NC}"
wait_for_deployment "loom" "timescaledb" 180
wait_for_deployment "loom" "kafka" 180

# Wait for database migration job
echo -e "\n${BLUE}🗄️  Waiting for database migrations...${NC}"
wait_for_job "loom" "db-migration" 300

# Wait for application services
echo -e "\n${BLUE}🚀 Waiting for application services...${NC}"
wait_for_deployment "loom" "ingestion-api" 120
wait_for_deployment "loom" "kafka-ui" 60

# Optional: Wait for VAD processor (may not have image built yet)
echo -e "\n${BLUE}🤖 Checking VAD processor status...${NC}"
if kubectl get deployment vad-processor -n loom &> /dev/null; then
    wait_for_deployment "loom" "vad-processor" 120 || echo -e "${YELLOW}⚠️  VAD processor deployment exists but may not be ready (image might be missing)${NC}"
fi

# Show deployment status
echo -e "\n${BLUE}📋 Deployment Status:${NC}"
kubectl get pods -n loom -o wide

echo -e "\n${BLUE}🌐 Service Endpoints:${NC}"
kubectl get services -n loom

echo -e "\n${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo -e "${BLUE}Access the services:${NC}"
echo "  🔗 Ingestion API:    http://localhost:30000"
echo "  🔗 API Docs:         http://localhost:30000/docs"
echo "  🔗 Kafka UI:         http://localhost:30081"
echo "  🔗 TimescaleDB:      localhost:30432 (user: loom, password: loom)"
echo "  🔗 Kafka:            localhost:30092"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  📊 Check status:     kubectl get pods -n loom"
echo "  📝 View logs:        kubectl logs -f deployment/ingestion-api -n loom"
echo "  🧪 Run tests:       ./scripts/test-deployment.sh"
echo "  🧹 Cleanup:         k3d cluster delete $CLUSTER_NAME"
