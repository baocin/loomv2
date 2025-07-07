# Apply Kafka to DB Consumer Fix

## Prerequisites
Ensure your k3d cluster is running and kubectl is properly configured:
```bash
# Start k3d cluster
k3d cluster start loom-local

# Get kubeconfig
k3d kubeconfig merge loom-local --kubeconfig-merge-default

# Verify connection
kubectl get nodes
```

## Step 1: Build and Push Docker Image
```bash
cd services/kafka-to-db-consumer
make docker
make docker-push
```

## Step 2: Deploy Optimized Configuration
```bash
# From project root
helm upgrade --install kafka-to-db-consumer deploy/helm/kafka-to-db-consumer/ \
    -n loom-dev \
    --create-namespace \
    --wait \
    --timeout 5m
```

## Step 3: Scale Deployment
```bash
# Scale to 3 replicas
kubectl scale deployment kafka-to-db-consumer -n loom-dev --replicas=3

# Verify pods are running
kubectl get pods -n loom-dev -l app=kafka-to-db-consumer
```

## Step 4: Monitor Progress
```bash
# Monitor consumer lag
./scripts/monitor-consumer-lag.sh

# Watch logs
kubectl logs -n loom-dev deployment/kafka-to-db-consumer -f

# Check pod resources
kubectl top pods -n loom-dev | grep kafka-to-db-consumer
```

## What Was Changed

### Code Changes
1. **Database Connection Pool**: Increased from 2-10 to 10-50 connections
2. **Batch Processing**: Added batch insert capability (200 messages/batch)
3. **Kafka Consumer Settings**: Optimized for throughput
4. **Activity Logging**: Integrated with ConsumerActivityLogger

### Configuration Changes
1. **Resources**: 1GB-2GB RAM, 1-2 CPU cores per pod
2. **Replicas**: 3 initial replicas with autoscaling 3-10
3. **Environment Variables**:
   - `LOOM_KAFKA_BATCH_SIZE=200`
   - `LOOM_KAFKA_BATCH_TIMEOUT=0.5`
   - `LOOM_DB_MIN_POOL_SIZE=20`
   - `LOOM_DB_MAX_POOL_SIZE=100`

### Expected Results
- 10-20x improvement in message processing rate
- Consumer lag should decrease rapidly
- Stable performance under load
- Automatic scaling based on CPU/memory usage

## Troubleshooting

If the deployment fails or lag persists:

1. **Check logs for errors**:
   ```bash
   kubectl logs -n loom-dev deployment/kafka-to-db-consumer --tail=100
   ```

2. **Verify database connectivity**:
   ```bash
   kubectl exec -n loom-dev deployment/kafka-to-db-consumer -- env | grep DATABASE_URL
   ```

3. **Check Kafka connectivity**:
   ```bash
   kubectl exec -n loom-dev deployment/kafka-to-db-consumer -- env | grep KAFKA
   ```

4. **Manually increase replicas if needed**:
   ```bash
   kubectl scale deployment kafka-to-db-consumer -n loom-dev --replicas=5
   ```

## Rollback (if needed)
```bash
# Rollback to previous version
helm rollback kafka-to-db-consumer -n loom-dev

# Or redeploy with original values
helm upgrade kafka-to-db-consumer deploy/helm/kafka-to-db-consumer/ \
    -n loom-dev \
    --set replicaCount=1 \
    --set resources.limits.cpu=500m \
    --set resources.limits.memory=512Mi \
    --set autoscaling.enabled=false
```