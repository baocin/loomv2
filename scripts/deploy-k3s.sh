#!/bin/bash
# Simple deployment script for local k3s
# No SSH, no image transfers - much easier!

set -e

NAMESPACE="loom-dev"

echo "🚀 Deploying to local k3s"
echo "========================="

# Check k3s is running
if ! kubectl get nodes &>/dev/null; then
    echo "❌ k3s not accessible. Run ./scripts/setup-k3s-local.sh first"
    exit 1
fi

# Build image
echo "📦 Building ingestion-api image..."
cd services/ingestion-api
docker build -t loom-ingestion-api:latest .
cd ../..

# Import image to k3s
echo "📤 Importing image to k3s..."
docker save loom-ingestion-api:latest | sudo k3s ctr images import -

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
echo "🔗 URLs (via port-forward):"
echo "  Ingestion API: kubectl port-forward svc/ingestion-api 8000:80 -n ${NAMESPACE}"
echo "  Then visit: http://localhost:8000"
echo ""
echo "🧪 Quick test:"
echo "  kubectl port-forward svc/ingestion-api-external 8000:8000 -n ${NAMESPACE} &"
echo "  curl http://localhost:8000/healthz"
echo ""
echo "📝 Useful commands:"
echo "  kubectl logs -f deployment/ingestion-api -n ${NAMESPACE}"
echo "  kubectl exec -it deployment/kafka -n ${NAMESPACE} -- kafka-topics --list --bootstrap-server localhost:9092" 