#!/bin/bash
# Simple deployment script for k3s in multipass VM
# Real k3s deployment - just like production!

set -e

NAMESPACE="loom-dev"
VM_NAME="k3s"

echo "🚀 Deploying to k3s in multipass VM"
echo "===================================="

# Check k3s is running
if ! kubectl get nodes &>/dev/null; then
    echo "❌ k3s cluster not accessible. Run ./scripts/setup-k3s-local.sh first"
    exit 1
fi

# Build image
echo "📦 Building ingestion-api image..."
cd services/ingestion-api
docker build -t loom-ingestion-api:latest .
cd ../..

# Import image to multipass VM
echo "📤 Importing image to multipass VM..."
docker save loom-ingestion-api:latest > /tmp/loom-ingestion-api.tar
multipass transfer /tmp/loom-ingestion-api.tar "$VM_NAME":/tmp/
multipass exec "$VM_NAME" -- sudo k3s ctr images import /tmp/loom-ingestion-api.tar
rm /tmp/loom-ingestion-api.tar

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
# Get VM IP for direct access
VM_IP=$(multipass info "$VM_NAME" | grep IPv4 | awk '{print $2}')

echo "🔗 Access URLs:"
echo "  Direct via VM IP:"
echo "    Ingestion API: http://$VM_IP:32080"
echo "    Kafka: $VM_IP:32092"
echo ""
echo "  Via port-forward (recommended):"
echo "    kubectl port-forward svc/ingestion-api-external 8000:8000 -n ${NAMESPACE}"
echo "    Then: http://localhost:8000"
echo ""
echo "🧪 Quick test:"
echo "  # Via port-forward:"
echo "  kubectl port-forward svc/ingestion-api-external 8000:8000 -n ${NAMESPACE} &"
echo "  curl http://localhost:8000/healthz"
echo ""
echo "  # Or direct via VM IP:"
echo "  curl http://$VM_IP:32080/healthz"
echo ""
echo "📝 Useful commands:"
echo "  kubectl logs -f deployment/ingestion-api -n ${NAMESPACE}"
echo "  kubectl exec -it deployment/kafka -n ${NAMESPACE} -- kafka-topics --list --bootstrap-server localhost:9092"
echo "  multipass shell $VM_NAME  # SSH into the VM"
echo ""
echo "🧹 Cleanup:"
echo "  kubectl delete namespace ${NAMESPACE}  # Remove our apps"
echo "  multipass delete $VM_NAME && multipass purge  # Remove VM" 