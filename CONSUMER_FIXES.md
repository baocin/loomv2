# Kafka Consumer Stalling Fixes

## Root Cause
All consumers were stalling after processing ~10 messages due to:

1. **Recursive Retry Bug** in silero-vad consumer causing stack overflow
2. **Per-message commits** causing performance issues
3. **Short polling timeouts** (1 second) causing frequent empty polls
4. **Missing Kafka session/heartbeat configuration** leading to consumer timeouts
5. **Synchronous blocking operations** in some consumers (GPS geocoding)

## Fixes Applied

### 1. Fixed Recursive Retry Bug (silero-vad)
- Changed from recursive retry to loop-based retry
- Added max retry limit (3 attempts)
- Prevents stack overflow on message failures

### 2. Implemented Batch Commit Strategy
- Commit every 100 messages or 5 seconds (whichever comes first)
- Reduces Kafka broker load
- Improves throughput significantly

### 3. Updated Kafka Consumer Configuration
```python
session_timeout_ms=30000      # 30 seconds (was default 10s)
heartbeat_interval_ms=3000    # 3 seconds (was default 3s)
max_poll_interval_ms=300000   # 5 minutes for slow processing (was default 5min)
consumer_timeout_ms=5000      # 5 seconds (was 1s)
```

### 4. Updated BaseKafkaConsumer
- Added batch commit logic
- Added proper timeout configurations
- Improved error handling

### 5. Created Async GPS Geocoding Consumer
- Replaced synchronous consumer with async version
- Removed blocking `time.sleep()` calls
- Added proper async database operations

## Services Updated
- ✅ silero-vad consumer - Fixed recursive bug, batch commits, timeouts
- ✅ BaseKafkaConsumer (loom-common) - Added batch commits and timeouts
- ✅ GPS geocoding - Created async version (async_consumer.py)

## Services Still Needing Updates
The following services still use synchronous consumers or need batch commit updates:
- significant-motion-detector
- georegion-detector
- activity-classifier
- step-counter
- face-emotion (async but commits per message)
- bud-e-emotion (async but commits per message)
- Other async consumers using AIOKafkaConsumer directly

## How to Apply Fixes to Remaining Consumers

### For Synchronous Consumers:
1. Convert to use BaseKafkaConsumer from loom-common
2. Or create async version using AIOKafkaConsumer with proper config

### For Async Consumers:
1. Add batch commit logic
2. Update timeout configurations
3. Remove per-message commits

## Testing the Fixes

To restart affected services and test:

```bash
# Restart the updated services
kubectl rollout restart deployment/silero-vad -n loom-dev
kubectl rollout restart deployment/gps-geocoding-consumer -n loom-dev

# Check logs
kubectl logs -f deployment/silero-vad -n loom-dev
kubectl logs -f deployment/gps-geocoding-consumer -n loom-dev

# Monitor consumer lag
kubectl exec -it deployment/kafka -n loom-dev -- kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --all-groups
```

## Expected Results
- Consumers should process messages continuously without stalling
- Batch commits should show in logs every 5 seconds or 100 messages
- No more recursive retry stack overflows
- Better throughput and lower latency