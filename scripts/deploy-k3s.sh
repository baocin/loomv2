#!/bin/bash
# Simple deployment script for k3d cluster
# Fast and simple - perfect for development!

set -e

NAMESPACE="loom-dev"
CLUSTER_NAME="loom-local"

echo "🚀 Deploying to k3d cluster"
echo "============================"

# Check k3d is running
if ! kubectl get nodes &>/dev/null; then
    echo "❌ k3d cluster not accessible. Run ./scripts/setup-k3s-local.sh first"
    exit 1
fi

# Build image
echo "📦 Building ingestion-api image..."
cd services/ingestion-api
docker build -t loom-ingestion-api:latest .
cd ../..

# Import image to k3d
echo "📤 Importing image to k3d..."
k3d image import loom-ingestion-api:latest -c "$CLUSTER_NAME"

echo "✅ Image imported successfully!"

# Deploy manifests
echo "🎯 Deploying to k3s..."
kubectl apply -f deploy/dev/namespace.yaml
kubectl apply -f deploy/dev/kafka.yaml
kubectl apply -f deploy/dev/ingestion-api.yaml

# Wait for pods
echo "⏳ Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=zookeeper -n ${NAMESPACE} --timeout=120s
kubectl wait --for=condition=ready pod -l app=kafka -n ${NAMESPACE} --timeout=180s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingestion-api -n ${NAMESPACE} --timeout=120s

# Show status
echo "✅ Deployment complete!"
echo ""
echo "📊 Status:"
kubectl get pods -n ${NAMESPACE}
echo ""
echo "🌐 Services:"
kubectl get svc -n ${NAMESPACE}
echo ""
echo "🔗 Access URLs (via k3d port mapping):"
echo "  Ingestion API: http://localhost:8000"
echo "  Kafka: localhost:9092"
echo ""
echo "🧪 Quick test:"
echo "  curl http://localhost:8000/healthz"
echo "  curl http://localhost:8000/docs"
echo ""
echo "📝 Useful commands:"
echo "  kubectl logs -f deployment/ingestion-api -n ${NAMESPACE}"
echo "  kubectl exec -it deployment/kafka -n ${NAMESPACE} -- kafka-topics --list --bootstrap-server localhost:9092"
echo "  k3d cluster list  # Show clusters"
echo ""
echo "🧹 Cleanup:"
echo "  kubectl delete namespace ${NAMESPACE}  # Remove our apps"
echo "  k3d cluster delete ${CLUSTER_NAME}  # Remove cluster" 