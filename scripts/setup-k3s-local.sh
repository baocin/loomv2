#!/bin/bash
# Setup k3s locally for simple development
# Much easier than remote cluster!

set -e

echo "🐄 Setting up local k3s cluster"
echo "==============================="

# Check if k3s is already installed
if command -v k3s &> /dev/null; then
    echo "✅ k3s is already installed"
else
    echo "📦 Installing k3s..."
    curl -sfL https://get.k3s.io | sh -
    
    # Wait for k3s to start
    echo "⏳ Waiting for k3s to start..."
    sleep 10
fi

# Setup kubectl to use k3s
echo "🔧 Setting up kubectl..."
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config 2>/dev/null || {
    mkdir -p ~/.kube
    sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
}
sudo chown $(whoami):$(whoami) ~/.kube/config

# Test connection
echo "🧪 Testing connection..."
if kubectl get nodes; then
    echo "✅ k3s is ready!"
    echo ""
    echo "📊 Cluster info:"
    kubectl cluster-info
    echo ""
    echo "🎯 Next steps:"
    echo "  1. Build images: docker build -t loom-ingestion-api:latest services/ingestion-api/"
    echo "  2. Import to k3s: sudo k3s ctr images import <(docker save loom-ingestion-api:latest)"
    echo "  3. Deploy: kubectl apply -f deploy/dev/"
    echo ""
    echo "🚀 Or use the deploy script: ./scripts/deploy-k3s.sh"
else
    echo "❌ Failed to connect to k3s"
    exit 1
fi 