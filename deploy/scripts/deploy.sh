#!/bin/bash
# Deployment script for Loom ingestion API

set -e

CLUSTER_IP="10.0.0.148"
NAMESPACE="loom-dev"

echo "🚀 Deploying Loom Ingestion API to k8s cluster at ${CLUSTER_IP}"

# Step 1: Build Docker image
echo "📦 Building Docker image..."
cd services/ingestion-api
docker build -t loom-ingestion-api:latest .
cd ../..

# Step 2: Export image for k8s cluster
echo "📤 Preparing image for k8s cluster..."
docker save loom-ingestion-api:latest > /tmp/loom-ingestion-api.tar

# Step 3: Copy image to k8s node (you'll need SSH access)
echo "🚚 Copying image to k8s cluster..."
echo "⚠️  You need to manually copy the image:"
echo "   scp /tmp/loom-ingestion-api.tar user@${CLUSTER_IP}:/tmp/"
echo "   ssh user@${CLUSTER_IP} 'docker load < /tmp/loom-ingestion-api.tar'"
echo ""
echo "Press Enter when image is loaded on cluster..."
read

# Step 4: Deploy to k8s
echo "🎯 Deploying to k8s..."
kubectl apply -f deploy/dev/namespace.yaml
kubectl apply -f deploy/dev/kafka.yaml
kubectl apply -f deploy/dev/ingestion-api.yaml

# Step 5: Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=ready pod -l app=zookeeper -n ${NAMESPACE} --timeout=120s
kubectl wait --for=condition=ready pod -l app=kafka -n ${NAMESPACE} --timeout=180s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingestion-api -n ${NAMESPACE} --timeout=120s

# Step 6: Show status
echo "✅ Deployment complete!"
echo ""
echo "📊 Cluster Status:"
kubectl get pods -n ${NAMESPACE}
echo ""
echo "🌐 Service URLs:"
echo "  Ingestion API: http://${CLUSTER_IP}:32080"
echo "  Kafka (external): ${CLUSTER_IP}:32092"
echo ""
echo "🔍 Useful commands:"
echo "  kubectl logs -f deployment/ingestion-api -n ${NAMESPACE}"
echo "  kubectl port-forward svc/ingestion-api 8000:80 -n ${NAMESPACE}"
echo "  kubectl exec -it deployment/kafka -n ${NAMESPACE} -- kafka-topics --list --bootstrap-server localhost:9092" 