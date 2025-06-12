#!/bin/bash
# Setup k3d (k3s in Docker) for local development
# Simple and fast - perfect for macOS!

set -e

CLUSTER_NAME="loom-local"

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🐄 Setting up k3d cluster"
echo "========================="

# Check if k3d is installed
if ! command -v k3d &> /dev/null; then
    echo "📦 Installing k3d..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install k3d
        else
            curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
        fi
    else
        # Linux
        curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
    fi
    echo "✅ k3d installed!"
else
    echo "✅ k3d is already installed"
fi

# Check if cluster exists
if k3d cluster list | grep -q "$CLUSTER_NAME"; then
    echo "✅ Cluster $CLUSTER_NAME already exists"
    k3d cluster start "$CLUSTER_NAME" 2>/dev/null || true
else
    echo "🚀 Creating k3d cluster..."
    k3d cluster create "$CLUSTER_NAME" \
        --port "8000:32080@loadbalancer" \
        --port "9092:32092@loadbalancer" \
        --wait
fi

# Setup kubectl context
echo "🔧 Setting up kubectl context..."
k3d kubeconfig merge "$CLUSTER_NAME" --kubeconfig-switch-context

# Test connection
echo "🧪 Testing connection..."
if kubectl get nodes; then
    echo "✅ k3d cluster is ready!"
    echo ""
    echo "📊 Cluster info:"
    kubectl cluster-info
    echo ""
    echo "🎯 Cluster details:"
    echo "  Name: $CLUSTER_NAME"
    echo "  Ports: 8000 (API), 9092 (Kafka)"
    echo ""
    echo "🚀 Next steps:"
echo "  1. Deploy: $SCRIPT_DIR/deploy-k3s.sh"
    echo ""
    echo "🧹 Cleanup commands:"
    echo "  Stop: k3d cluster stop $CLUSTER_NAME"
    echo "  Delete: k3d cluster delete $CLUSTER_NAME"
else
    echo "❌ Failed to connect to k3d cluster"
    exit 1
fi 