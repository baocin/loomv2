# Rename Twitter Images Topic for Clarity

## Current Issue
The topic `external.twitter.images.raw` is ambiguous. It doesn't clearly indicate that these are **screenshots of Twitter posts** rather than **images extracted from posts**.

## Current Data Flow
1. **X URL Processor** → Takes Twitter URLs
2. **Screenshots** → Creates screenshots of entire tweets
3. **Sends to** → `external.twitter.images.raw`
4. **Twitter OCR Processor** → Reads screenshots and extracts text via OCR

## Suggested Renaming Options

### Option 1: Descriptive Naming (Recommended)
```
external.twitter.images.raw → external.twitter.screenshots.raw
```

### Option 2: More Specific
```
external.twitter.images.raw → external.twitter.post_screenshots.raw
```

### Option 3: OCR-Focused
```
external.twitter.images.raw → external.twitter.screenshots_for_ocr.raw
```

## Files That Need Updates

### 1. Topic Creation Script
```python
# scripts/create_kafka_topics.py
RAW_TOPICS: List[str] = [
    # ...
    "external.twitter.liked.raw",
    "external.twitter.screenshots.raw",  # Changed from external.twitter.images.raw
    # ...
]
```

### 2. X URL Processor
```python
# services/x-url-processor/app/main.py (line 128)
self.kafka_producer.send_message(
    topic="external.twitter.screenshots.raw",  # Changed
    key=tweet_data.get("tweet_id", url),
    value=image_message,
)
```

### 3. Twitter OCR Processor
```python
# services/twitter-ocr-processor/app/main.py (line 201)
self.input_topic = "external.twitter.screenshots.raw"  # Changed
```

### 4. Documentation Updates
- Update pipeline diagrams
- Update API documentation
- Update monitoring queries

## Migration Strategy

### Option A: Clean Rename (Recommended for Dev)
1. Update all code references
2. Create new topic with correct name
3. Delete old topic
4. Restart services

### Option B: Gradual Migration (Production)
1. Create new topic alongside old one
2. Update producers to write to both topics
3. Update consumers to read from new topic
4. Remove old topic after verification

## Implementation

### Quick Fix Script
```bash
#!/bin/bash
# Rename topic from external.twitter.images.raw to external.twitter.screenshots.raw

NAMESPACE="${NAMESPACE:-loom-dev}"
KAFKA_POD=$(kubectl get pods -n $NAMESPACE -l app=kafka -o jsonpath='{.items[0].metadata.name}')

# Create new topic
kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --topic external.twitter.screenshots.raw \
    --partitions 3 \
    --replication-factor 1

# Delete old topic (optional, for clean migration)
kubectl exec -n $NAMESPACE $KAFKA_POD -- kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --delete \
    --topic external.twitter.images.raw
```

## Recommended Action

I recommend **Option 1** (`external.twitter.screenshots.raw`) because:
- ✅ **Clear**: Immediately indicates these are screenshots
- ✅ **Concise**: Short but descriptive
- ✅ **Consistent**: Follows existing naming pattern
- ✅ **Future-proof**: If we add actual embedded images later, they can use `external.twitter.media.raw`

## Impact Assessment
- **Low Risk**: Only affects two services
- **No Data Loss**: Simple topic rename
- **Easy Rollback**: Can revert changes quickly
- **Improved Clarity**: Makes pipeline easier to understand
