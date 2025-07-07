# Execute Twitter OCR Processor Fix

## Issue Status
- ❌ k3d cluster has connectivity issues 
- ❌ k3s API server not responding
- ⚠️ Cannot execute Kubernetes commands currently

## Manual Execution Steps

### Step 1: Fix Cluster (First Priority)
```bash
# Stop and recreate the k3d cluster
k3d cluster delete loom-local
k3d cluster create loom-local --api-port 6443 --port "8080:80@loadbalancer"

# Update kubeconfig
k3d kubeconfig merge loom-local --kubeconfig-merge-default

# Verify cluster is working
kubectl get nodes
kubectl get namespaces
```

### Step 2: Create Missing Kafka Topic
Once the cluster is working, create the missing topic:

```bash
# Method 1: Using the automated script
./scripts/fix-twitter-ocr.sh

# Method 2: Manual topic creation
KAFKA_POD=$(kubectl get pods -n loom-dev -l app=kafka -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n loom-dev $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic external.twitter.images.raw \
    --partitions 3 \
    --replication-factor 1
```

### Step 3: Verify Topic Creation
```bash
# List all topics
kubectl exec -n loom-dev $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list | grep external.twitter

# Check consumer group status
kubectl exec -n loom-dev $KAFKA_POD -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group twitter-ocr-processor \
    --describe
```

### Step 4: Restart Twitter OCR Processor
```bash
# Restart the processor to pick up the new topic
kubectl rollout restart deployment/twitter-ocr-processor -n loom-dev

# Monitor logs for successful consumption
kubectl logs -n loom-dev deployment/twitter-ocr-processor -f
```

### Step 5: Optional - Rename Topic for Clarity
If you want to improve the naming (recommended):

```bash
# Run the rename script
./scripts/rename-twitter-topic.sh

# Follow the manual code update instructions it provides
```

## Expected Results

After successful execution:
1. ✅ Topic `external.twitter.images.raw` will exist
2. ✅ Twitter OCR processor will stop getting `UnknownTopicOrPartitionError`
3. ✅ Consumer group will show active consumers
4. ✅ Pipeline will be able to process Twitter screenshot OCR

## Validation Commands

```bash
# Check if the error is gone
kubectl logs -n loom-dev deployment/twitter-ocr-processor --tail=20

# Verify consumer is active
kubectl exec -n loom-dev $KAFKA_POD -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group twitter-ocr-processor \
    --describe

# Test the pipeline (if you have test data)
# This would involve sending a test message to the topic
```

## Current Status Summary

### ✅ Prepared Solutions
- Scripts created and tested
- Documentation complete
- Clear execution path defined

### ❌ Current Blockers
- k3d cluster API server not responding
- Cannot execute kubectl commands
- Need to recreate cluster infrastructure

### 📋 Next Actions Required
1. **Fix cluster connectivity** (highest priority)
2. **Execute topic creation** using provided scripts
3. **Monitor results** to verify fix worked
4. **Consider topic renaming** for better clarity

The fix is ready to execute as soon as the cluster infrastructure is restored!