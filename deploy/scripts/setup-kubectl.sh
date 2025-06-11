#!/bin/bash
# Script to configure kubectl access to the k8s cluster

set -e

CLUSTER_IP="10.0.0.148"
CLUSTER_NAME="loom-local"
CONTEXT_NAME="loom-local"

echo "🔧 Setting up kubectl access to k8s cluster at ${CLUSTER_IP}"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    echo "   https://kubernetes.io/docs/tasks/tools/install-kubectl/"
    exit 1
fi

echo "📝 Configuring cluster access..."

# Option 1: Basic insecure setup (for development)
echo "Setting up insecure connection (development only)..."
kubectl config set-cluster ${CLUSTER_NAME} \
    --server=https://${CLUSTER_IP}:6443 \
    --insecure-skip-tls-verify=true

kubectl config set-context ${CONTEXT_NAME} \
    --cluster=${CLUSTER_NAME}

kubectl config use-context ${CONTEXT_NAME}

echo "✅ kubectl configured!"
echo ""
echo "🧪 Testing connection..."

if kubectl get nodes; then
    echo "✅ Successfully connected to k8s cluster!"
    echo ""
    echo "📊 Cluster Info:"
    kubectl cluster-info
    echo ""
    echo "🎯 You can now run:"
    echo "   ./deploy/scripts/deploy.sh"
else
    echo "❌ Failed to connect to cluster."
    echo ""
    echo "🔍 Troubleshooting:"
    echo "1. Check if the cluster is running at ${CLUSTER_IP}:6443"
    echo "2. Verify you have network access to the cluster"
    echo "3. Check if the cluster uses a different port"
    echo "4. You may need authentication - check with your cluster admin"
fi 