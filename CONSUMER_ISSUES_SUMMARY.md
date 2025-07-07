# Consumer Issues Summary & Fixes

## Issue 1: Kafka to DB Consumer Lag ✅ FIXED

### Problem
The Kafka to DB consumer had massive lag, unable to keep up with message throughput.

### Root Cause
- Small database connection pool (2-10 connections)
- Single replica processing messages sequentially
- Individual message processing (no batching)
- Limited resources (512Mi RAM, 500m CPU)

### Solution Applied
1. **Database Connection Pool**: 2-10 → 20-50 connections
2. **Batch Processing**: 200 messages per batch, 0.5s timeout
3. **Horizontal Scaling**: 1 → 3 replicas with autoscaling (3-10)
4. **Resource Increase**: 512Mi→2Gi RAM, 500m→2000m CPU
5. **Kafka Optimizations**: Larger fetch sizes, optimized polling

### Files Modified
- `services/kafka-to-db-consumer/app/main.py` - Added batch processing
- `deploy/helm/kafka-to-db-consumer/values.yaml` - Scaled resources
- `scripts/monitor-consumer-lag.sh` - Monitoring script
- `scripts/fix-consumer-lag.sh` - Automated fix

### Expected Results
- 10-20x throughput improvement
- Lag reduction from hours to minutes
- Automatic scaling under load

---

## Issue 2: Twitter OCR Processor Missing Topic ⚠️ NEEDS FIX

### Problem
```
Group twitter-ocr-processor failed to commit partition TopicPartition(topic='external.twitter.images.raw', partition=1) at offset OffsetAndMetadata(offset=0, metadata=''): UnknownTopicOrPartitionError
```

### Root Cause
The Kafka topic `external.twitter.images.raw` doesn't exist, but the twitter-ocr-processor is trying to consume from it.

### ⚠️ NAMING ISSUE
The topic name `external.twitter.images.raw` is **misleading**. It actually contains:
- **Screenshots of entire Twitter/X posts** (for OCR text extraction)
- **NOT** embedded images from within posts

**Better name**: `external.twitter.screenshots.raw`

### Solution
Create the missing topic and related topics:

```bash
# Quick fix when cluster is available
./scripts/fix-twitter-ocr.sh

# Or manually
kubectl exec -n loom-dev deployment/kafka -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic external.twitter.images.raw \
    --partitions 3 \
    --replication-factor 1
```

### Files Created
- `scripts/fix-twitter-ocr.sh` - Automated fix script (creates topic with current name)
- `scripts/rename-twitter-topic.sh` - Rename to better name
- `FIX_TWITTER_OCR_PROCESSOR.md` - Detailed instructions
- `RENAME_TWITTER_TOPIC.md` - Naming improvement guide

### Required Topics
- `external.twitter.images.raw` ❌ Missing
- `external.twitter.liked.raw`
- `media.image.analysis.moondream_results`
- `media.text.ocr_extracted`
- `media.text.ocr_cleaned`

---

## Current Status

### ✅ Completed Fixes
1. **Kafka to DB Consumer Optimization** - Code and configuration ready
2. **Monitoring Scripts** - Available for both issues
3. **Documentation** - Comprehensive fix instructions

### ⚠️ Pending Actions (Requires Running Cluster)
1. **Deploy optimized Kafka to DB consumer**:
   ```bash
   ./scripts/fix-consumer-lag.sh
   ```

2. **Create missing topics for Twitter OCR**:
   ```bash
   ./scripts/fix-twitter-ocr.sh
   ```

3. **Monitor results**:
   ```bash
   ./scripts/monitor-consumer-lag.sh
   ```

### 🚫 Current Blockers
- k3d cluster connectivity issues
- Kafka not accessible on expected ports
- Need to restart/reconfigure cluster

---

## Quick Recovery Steps

### 1. Fix Cluster Connectivity
```bash
# Restart k3d cluster
k3d cluster stop loom-local
k3d cluster start loom-local

# Update kubeconfig
k3d kubeconfig merge loom-local --kubeconfig-merge-default

# Verify connection
kubectl get nodes
```

### 2. Apply All Fixes
```bash
# Fix missing topics
./scripts/fix-twitter-ocr.sh

# Deploy optimized consumer
./scripts/fix-consumer-lag.sh

# Monitor progress
./scripts/monitor-consumer-lag.sh
```

### 3. Verify Resolution
```bash
# Check consumer lag
kubectl exec -n loom-dev deployment/kafka -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --describe

# Check service logs
kubectl logs -n loom-dev deployment/kafka-to-db-consumer --tail=50
kubectl logs -n loom-dev deployment/twitter-ocr-processor --tail=50
```

---

## Expected Outcomes

After applying both fixes:
1. **Kafka to DB Consumer**: Lag should drop dramatically with parallel processing
2. **Twitter OCR Processor**: Should start consuming successfully without errors
3. **Overall Pipeline**: Improved throughput and reduced bottlenecks

The Kafka to DB consumer fix addresses the major bottleneck, while the Twitter OCR fix resolves a configuration issue preventing that processor from starting properly.
