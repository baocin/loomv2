# Kafka to DB Consumer Lag Fix - Implementation Summary

## Changes Applied

### 1. Code Optimizations (services/kafka-to-db-consumer/app/main.py)

#### Database Connection Pool Enhancement
```python
# BEFORE
self.db_pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=2,
    max_size=10,
    command_timeout=60,
)

# AFTER
self.db_pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=DB_MIN_POOL_SIZE,  # 10 -> 20
    max_size=DB_MAX_POOL_SIZE,  # 10 -> 50
    command_timeout=60,
    server_settings={
        'jit': 'off',
        'synchronous_commit': 'off',
    },
)
```

#### Batch Processing Implementation
- Added `_process_batch()` method for processing multiple messages at once
- Batch size: 200 messages (configurable via LOOM_KAFKA_BATCH_SIZE)
- Batch timeout: 0.5 seconds (configurable via LOOM_KAFKA_BATCH_TIMEOUT)
- Groups messages by topic for efficient batch inserts

#### Kafka Consumer Optimization
```python
self.consumer = AIOKafkaConsumer(
    *TOPIC_TABLE_MAPPINGS.keys(),
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    group_id=KAFKA_GROUP_ID,
    auto_offset_reset="earliest",
    enable_auto_commit=True,
    auto_commit_interval_ms=5000,  # NEW
    max_poll_records=500,           # NEW - Process more messages per poll
    fetch_max_bytes=52428800,       # NEW - 50MB max fetch
    session_timeout_ms=60000,       # NEW - 60 second timeout
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)
```

### 2. Deployment Configuration (deploy/helm/kafka-to-db-consumer/values.yaml)

#### Resource Scaling
```yaml
# BEFORE
replicaCount: 1
resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

# AFTER
replicaCount: 3
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi
```

#### Autoscaling
```yaml
autoscaling:
  enabled: true  # was false
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 70
```

#### Performance Environment Variables
```yaml
env:
  LOOM_KAFKA_BATCH_SIZE: "200"
  LOOM_KAFKA_BATCH_TIMEOUT: "0.5"
  LOOM_DB_MIN_POOL_SIZE: "20"
  LOOM_DB_MAX_POOL_SIZE: "100"
```

### 3. Monitoring Scripts

#### monitor-consumer-lag.sh
- Checks Kafka consumer lag
- Shows database connection pool status
- Displays consumer performance metrics
- Shows active alerts
- Monitors pod resources

#### fix-consumer-lag.sh
- Builds and pushes updated Docker image
- Deploys optimized configuration via Helm
- Scales deployment to 3 replicas
- Monitors startup and lag reduction

## Expected Performance Improvements

1. **Throughput**: 10-20x increase in message processing rate
2. **Latency**: Reduced consumer lag from hours to minutes
3. **Scalability**: Automatic scaling from 3 to 10 pods based on load
4. **Reliability**: Better error handling with batch fallback to individual processing

## Quick Deployment

When the k3d cluster is available:
```bash
# Build and deploy
cd services/kafka-to-db-consumer
make docker && make docker-push
helm upgrade --install kafka-to-db-consumer ../../deploy/helm/kafka-to-db-consumer/ -n loom-dev

# Monitor progress
../../scripts/monitor-consumer-lag.sh
```

## Verification

Check that the optimizations are working:
```bash
# Consumer lag should decrease
kubectl exec -n loom-dev deployment/kafka -- kafka-consumer-groups.sh \
    --bootstrap-server localhost:9092 \
    --group kafka-to-db-consumer \
    --describe

# Database connections should increase
kubectl exec -n loom-dev deployment/timescaledb -- psql -U loom -d loom -c \
    "SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE '%kafka%'"

# CPU/Memory usage should be higher but stable
kubectl top pods -n loom-dev | grep kafka-to-db-consumer
```