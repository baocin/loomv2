# Fix Twitter OCR Processor - Missing Topic Error

## Problem
The twitter-ocr-processor is failing with `UnknownTopicOrPartitionError` for topic `external.twitter.images.raw`.

## Root Cause
The Kafka topic `external.twitter.images.raw` doesn't exist. The consumer is trying to consume from a non-existent topic.

## Solution

### Option 1: Create Missing Topics (Recommended)
```bash
# From project root, create all required topics
python scripts/create_kafka_topics.py --bootstrap-servers kafka:9092

# Or if running locally outside k8s
python scripts/create_kafka_topics.py --bootstrap-servers localhost:9092
```

### Option 2: Manual Topic Creation
```bash
# Connect to Kafka pod
kubectl exec -n loom-dev deployment/kafka -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic external.twitter.images.raw \
    --partitions 3 \
    --replication-factor 1

# Verify topic creation
kubectl exec -n loom-dev deployment/kafka -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list | grep external.twitter.images.raw
```

### Option 3: Quick Fix via k8s
```bash
# If k3d cluster is running
KAFKA_POD=$(kubectl get pods -n loom-dev -l app=kafka -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n loom-dev $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic external.twitter.images.raw \
    --partitions 3 \
    --replication-factor 1
```

## Verification
After creating the topic, verify the twitter-ocr-processor stops getting errors:

```bash
# Check consumer logs
kubectl logs -n loom-dev deployment/twitter-ocr-processor --tail=20

# Check consumer group status
kubectl exec -n loom-dev $KAFKA_POD -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group twitter-ocr-processor \
    --describe
```

## Prevention
To prevent this issue in the future:

1. **Always run topic creation script after cluster setup**:
   ```bash
   python scripts/create_kafka_topics.py --bootstrap-servers kafka:9092 --create-processed
   ```

2. **Add topic creation to deployment scripts**:
   - Include in `make dev-up` or similar commands
   - Add as init container in Helm charts

3. **Enable auto topic creation** (not recommended for production):
   ```yaml
   # In Kafka configuration
   auto.create.topics.enable: true
   ```

## Related Topics
The following topics should also exist for the pipeline to work properly:
- `external.twitter.liked.raw` - Input from Twitter scraper
- `external.twitter.images.raw` - Images extracted from tweets
- `media.image.analysis.moondream_results` - OCR results output
- `media.text.ocr_extracted` - Extracted text output

## Current Status
- ❌ `external.twitter.images.raw` topic missing
- ⚠️  twitter-ocr-processor failing to consume
- ⚠️  k3d cluster connection issues preventing immediate fix

## Next Steps
1. Ensure k3d cluster is running properly
2. Create missing topics using one of the methods above
3. Restart twitter-ocr-processor if needed
4. Monitor logs for successful consumption
