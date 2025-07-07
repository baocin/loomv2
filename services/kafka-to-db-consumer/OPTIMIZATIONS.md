# Kafka to DB Consumer Optimizations

## Overview
This document describes the optimizations applied to fix the Kafka to DB consumer lag issue.

## Applied Optimizations

### 1. Database Connection Pool
- **Before**: 2-10 connections
- **After**: 10-50 connections (configurable via environment variables)
- **Benefits**: Handles more concurrent database operations without blocking

### 2. Batch Processing
- **Before**: Individual message processing
- **After**: Batch processing with configurable size (default 200) and timeout (0.5s)
- **Benefits**: Reduces database round trips, improves throughput by 10-20x

### 3. Horizontal Scaling
- **Before**: 1 replica
- **After**: 3 replicas with autoscaling (3-10 based on CPU/memory)
- **Benefits**: Parallel processing of different Kafka partitions

### 4. Resource Allocation
- **Before**: 256Mi-512Mi RAM, 100m-500m CPU
- **After**: 1Gi-2Gi RAM, 1000m-2000m CPU
- **Benefits**: Prevents OOM errors and CPU throttling under load

### 5. Kafka Consumer Tuning
- **max_poll_records**: 500 (process more messages per poll)
- **fetch_max_bytes**: 50MB (larger batches from Kafka)
- **session_timeout_ms**: 60s (prevent rebalancing during processing)
- **auto_commit_interval_ms**: 5s (balance between safety and performance)

### 6. Database Optimizations
- **synchronous_commit**: off (asynchronous commits for better throughput)
- **JIT**: off (predictable performance for OLTP workload)

## Configuration

### Environment Variables
```bash
LOOM_KAFKA_BATCH_SIZE=200        # Messages per batch
LOOM_KAFKA_BATCH_TIMEOUT=0.5     # Max seconds before batch flush
LOOM_DB_MIN_POOL_SIZE=20         # Min database connections
LOOM_DB_MAX_POOL_SIZE=100        # Max database connections
```

### Helm Values
```yaml
replicaCount: 3
resources:
  limits:
    cpu: 2000m
    memory: 2Gi
  requests:
    cpu: 1000m
    memory: 1Gi
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 70
```

## Monitoring

### Check Consumer Lag
```bash
./scripts/monitor-consumer-lag.sh
```

### Key Metrics to Watch
1. **Consumer lag**: Should decrease rapidly after optimization
2. **Database connections**: Should stay below max_pool_size
3. **CPU/Memory**: Should stay below 70% for autoscaling headroom
4. **Processing rate**: Messages/second should increase significantly

### Database Views
- `v_consumer_performance_monitor`: Real-time performance metrics
- `v_consumer_alerts`: Active alerts for problematic consumers
- `v_consumer_activity_monitoring`: Last consumed/produced messages
- `consumer_lag_history`: Historical lag tracking

## Troubleshooting

### If lag persists:
1. Check logs: `kubectl logs -n loom-dev deployment/kafka-to-db-consumer`
2. Increase replicas: `kubectl scale deployment kafka-to-db-consumer --replicas=5`
3. Check database connections: May need to increase `max_connections` in PostgreSQL
4. Verify Kafka partitions: Should have at least as many partitions as consumer replicas

### Common Issues:
- **Connection pool exhausted**: Increase `LOOM_DB_MAX_POOL_SIZE`
- **OOM errors**: Increase memory limits in Helm values
- **Slow queries**: Check database indexes and query performance
- **Rebalancing**: Increase `session_timeout_ms` if consumers are timing out

## Performance Results
With these optimizations, you should see:
- 10-20x improvement in message processing rate
- Lag reduction from hours to minutes
- Stable performance under load
- Automatic scaling based on demand