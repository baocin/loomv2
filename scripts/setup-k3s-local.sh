#!/bin/bash
# Local k3d cluster setup for Loom development
# Creates a lightweight Kubernetes cluster with port forwarding

set -e

CLUSTER_NAME="loom-local"
REGISTRY_NAME="k3d-registry"
REGISTRY_PORT="5000"

echo "🐳 Setting up k3d cluster for Loom development"
echo "=============================================="

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
    echo "❌ k3d is not installed. Please install it first:"
    echo "   curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install it first."
    exit 1
fi

# Check if cluster already exists
if k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo "⚠️  Cluster '$CLUSTER_NAME' already exists. Deleting..."
    k3d cluster delete "$CLUSTER_NAME"
fi

# Check if registry already exists
if k3d registry list | grep -q "$REGISTRY_NAME"; then
    echo "⚠️  Registry '$REGISTRY_NAME' already exists. Deleting..."
    k3d registry delete "$REGISTRY_NAME"
fi

# Create local registry
echo "📦 Creating local container registry..."
k3d registry create "$REGISTRY_NAME" --port "$REGISTRY_PORT"

# Create k3d cluster with registry and port mappings
echo "🚀 Creating k3d cluster..."
k3d cluster create "$CLUSTER_NAME" \
  --api-port 6443 \
  --port "8000:8000@loadbalancer" \
  --port "9092:9092@loadbalancer" \
  --port "5432:5432@loadbalancer" \
  --port "3000:3000@loadbalancer" \
  --registry-use "k3d-$REGISTRY_NAME:$REGISTRY_PORT" \
  --agents 2 \
  --k3s-arg "--disable=traefik@server:0" \
  --wait

# Verify cluster is running  
echo "✅ Cluster created successfully!"

# Set kubectl context
kubectl config use-context "k3d-$CLUSTER_NAME"

# Wait for nodes to be ready
echo "⏳ Waiting for nodes to be ready..."
kubectl wait --for=condition=ready node --all --timeout=120s

# Create development namespace
echo "📁 Creating development namespace..."
kubectl create namespace loom-dev --dry-run=client -o yaml | kubectl apply -f -

# Show cluster info
echo ""
echo "🎉 k3d cluster setup complete!"
echo ""
echo "📊 Cluster Information:"
echo "  Cluster: $CLUSTER_NAME"
echo "  Registry: localhost:$REGISTRY_PORT"
echo "  Context: k3d-$CLUSTER_NAME"
echo ""
echo "🌐 Port Mappings:"
echo "  8000 -> Ingestion API"
echo "  9092 -> Kafka"
echo "  5432 -> PostgreSQL"
echo "  3000 -> Frontend (future)"
echo ""
echo "🔧 Useful Commands:"
echo "  kubectl get nodes"
echo "  kubectl get pods -n loom-dev"
echo "  k3d cluster list"
echo "  k3d registry list"
echo ""
echo "🏗️  Registry Usage:"
echo "  docker tag your-image:latest localhost:$REGISTRY_PORT/your-image:latest"
echo "  docker push localhost:$REGISTRY_PORT/your-image:latest"
echo "  k3d image import your-image:latest -c $CLUSTER_NAME"
echo ""
echo "🧹 Cleanup:"
echo "  k3d cluster delete $CLUSTER_NAME"
echo "  k3d registry delete $REGISTRY_NAME"
echo ""
echo "🚀 Next steps:"
echo "  ./scripts/deploy-k3s.sh  # Deploy services"
echo "  kubectl logs -f deployment/ingestion-api -n loom-dev  # Watch logs" 