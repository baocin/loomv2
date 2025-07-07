#!/bin/bash
# Fix Kafka to DB consumer lag by applying optimizations

set -euo pipefail

NAMESPACE="${NAMESPACE:-loom-dev}"

echo "=== Fixing Kafka to DB Consumer Lag ==="
echo "Namespace: $NAMESPACE"
echo ""

# Step 1: Build and push updated Docker image
echo "Step 1: Building updated Docker image..."
cd services/kafka-to-db-consumer
make docker
make docker-push
cd ../..

# Step 2: Update Helm deployment
echo ""
echo "Step 2: Deploying optimized configuration..."
helm upgrade kafka-to-db-consumer deploy/helm/kafka-to-db-consumer/ \
    -n $NAMESPACE \
    --wait \
    --timeout 5m

# Step 3: Wait for rollout
echo ""
echo "Step 3: Waiting for rollout to complete..."
kubectl rollout status deployment/kafka-to-db-consumer -n $NAMESPACE

# Step 4: Scale up replicas
echo ""
echo "Step 4: Scaling up replicas..."
kubectl scale deployment kafka-to-db-consumer -n $NAMESPACE --replicas=3

# Step 5: Monitor startup
echo ""
echo "Step 5: Monitoring startup..."
sleep 10
kubectl get pods -n $NAMESPACE -l app=kafka-to-db-consumer

# Step 6: Check consumer lag
echo ""
echo "Step 6: Checking consumer lag after optimization..."
./scripts/monitor-consumer-lag.sh

echo ""
echo "=== Optimization Summary ==="
echo "✅ Increased database connection pool: 10→50 connections"
echo "✅ Enabled batch processing: 200 messages per batch"
echo "✅ Scaled replicas: 1→3 instances"
echo "✅ Increased resources: 2GB RAM, 2 CPU cores per instance"
echo "✅ Enabled autoscaling: 3-10 replicas based on load"
echo "✅ Optimized Kafka consumer settings for throughput"
echo ""
echo "Monitor progress with: ./scripts/monitor-consumer-lag.sh"
echo "View logs with: kubectl logs -n $NAMESPACE deployment/kafka-to-db-consumer -f"
