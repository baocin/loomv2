# Kafka Consumer Optimization Guide

This guide explains how to use the Kafka consumer optimization system that has been added to Loom v2 to address consumer lag issues.

## Overview

The optimization system provides:
- **Per-service consumer configurations** stored in the database
- **Automatic partition recommendations** for high-volume topics
- **Real-time monitoring** of consumer performance
- **Configuration loaders** for Python and TypeScript services

## Database Tables

### `pipeline_consumer_configs`
Stores optimized Kafka consumer settings for each service:

```sql
-- View current configurations
SELECT service_name, max_poll_records, session_timeout_ms, description
FROM pipeline_consumer_configs
ORDER BY service_name;

-- Update a service's configuration
UPDATE pipeline_consumer_configs
SET max_poll_records = 50
WHERE service_name = 'moondream-vision-processor';
```

### `topic_partition_changes`
Tracks recommended partition count changes:

```sql
-- View partition recommendations
SELECT topic_name, current_partitions, recommended_partitions, reason
FROM topic_partition_changes
WHERE applied = false;

-- Generate Kafka admin commands to apply changes
SELECT generate_partition_update_script();
```

### Monitoring Tables
- `consumer_lag_history` - Time-series data of consumer lag
- `consumer_processing_metrics` - Processing performance metrics

## Using the Configuration Loaders

### Python Services

```python
from shared.kafka_consumer_config import KafkaConsumerConfigLoader
import asyncpg

# Initialize the loader
pool = await asyncpg.create_pool(DATABASE_URL)
loader = KafkaConsumerConfigLoader(pool)

# Load config for your service
config = await loader.load_config('my-service-name')

# Create an optimized consumer
consumer = await loader.create_consumer(
    service_name='my-service-name',
    topics=['device.audio.raw'],
    bootstrap_servers='kafka:9092'
)

# Or use the helper for polling with limits
async for messages in loader.poll_with_limit(consumer, 'my-service-name'):
    # Process messages in optimized batches
    for msg in messages:
        process_message(msg)
```

### TypeScript/Node.js Services

```typescript
import { createOptimizedConsumer } from './services/consumerConfigLoader';
import { Pool } from 'pg';

// Create database pool
const pool = new Pool({ connectionString: DATABASE_URL });

// Create optimized consumer
const consumer = await createOptimizedConsumer(
  pool,
  { brokers: ['kafka:9092'] },
  'my-service-name',
  ['device.audio.raw']
);

// Use the consumer
await consumer.run({
  eachBatch: async ({ batch }) => {
    // Process messages
  }
});
```

## Configuration Guidelines

### AI Model Services (GPU-intensive)
- `max_poll_records`: 1 (process one at a time)
- `max_poll_interval_ms`: 600000-1200000 (10-20 minutes)
- `session_timeout_ms`: 60000 (1 minute)
- Examples: moondream-vision-processor, minicpm-ocr-processor

### Fast Processing Services
- `max_poll_records`: 500-1000
- `max_poll_interval_ms`: 60000 (1 minute)
- `fetch_max_wait_ms`: 500 (batch collection)
- Examples: silero-vad-processor, motion-event-filter

### I/O Bound Services
- `max_poll_records`: 10-20
- `retry_backoff_ms`: 5000 (5 seconds)
- `request_timeout_ms`: 60000 (1 minute)
- Examples: geocoding-processor, url-scraper

### Database Writers
- `max_poll_records`: 1000 (large batches)
- `enable_auto_commit`: false (commit after DB write)
- Examples: timescale-writer, analytics-aggregator

## Monitoring Queries

### Check Consumer Lag
```sql
-- Current lag by service
SELECT * FROM v_consumer_performance_monitor
ORDER BY avg_lag DESC;

-- Services with active alerts
SELECT * FROM v_consumer_alerts;

-- Historical trends
SELECT * FROM v_consumer_performance_history
WHERE service_name = 'speech-processor'
AND timestamp > NOW() - INTERVAL '1 hour';
```

### Get Optimization Recommendations
```sql
-- In Python
recommendations = await loader.get_processing_recommendations()
for rec in recommendations:
    print(f"{rec['service_name']}: {rec['recommendation']}")
```

## Applying Partition Changes

1. Check recommendations:
```sql
SELECT * FROM v_partition_efficiency;
```

2. Generate update script:
```sql
SELECT generate_partition_update_script();
```

3. Run the generated Kafka commands:
```bash
# Example output:
kafka-topics --alter --topic device.sensor.accelerometer.raw --partitions 10
kafka-topics --alter --topic device.audio.raw --partitions 6
```

4. Mark as applied:
```sql
SELECT mark_partition_changes_applied();
```

## Troubleshooting

### High Consumer Lag

1. Check current configuration:
```sql
SELECT * FROM pipeline_consumer_configs
WHERE service_name = 'problematic-service';
```

2. View lag history:
```sql
SELECT timestamp, lag
FROM consumer_lag_history
WHERE service_name = 'problematic-service'
ORDER BY timestamp DESC
LIMIT 100;
```

3. Adjust configuration:
```sql
-- Increase batch size for faster processing
UPDATE pipeline_consumer_configs
SET max_poll_records = 100
WHERE service_name = 'problematic-service';
```

### Rebalancing Issues

If consumers are constantly rebalancing:
```sql
-- Increase timeouts
UPDATE pipeline_consumer_configs
SET
  session_timeout_ms = 120000,  -- 2 minutes
  max_poll_interval_ms = 900000  -- 15 minutes
WHERE service_name = 'slow-ai-processor';
```

### Memory Issues

For services running out of memory:
```sql
-- Reduce batch sizes
UPDATE pipeline_consumer_configs
SET
  max_poll_records = 10,
  fetch_max_bytes = 1048576  -- 1MB
WHERE service_name = 'memory-intensive-service';
```

## Best Practices

1. **Start Conservative**: Begin with smaller batch sizes and increase gradually
2. **Monitor Regularly**: Check the monitoring views daily
3. **Test Changes**: Update one service at a time and monitor impact
4. **Document Changes**: Update the description field when changing configs
5. **Use Recommendations**: The system provides data-driven recommendations

## Example: Optimizing a Slow Service

```sql
-- 1. Identify the problem
SELECT * FROM v_consumer_alerts
WHERE service_name = 'speech-processor';

-- 2. Check current config
SELECT * FROM pipeline_consumer_configs
WHERE service_name = 'speech-processor';

-- 3. View processing metrics
SELECT avg(processing_time_ms), avg(messages_per_second)
FROM consumer_processing_metrics
WHERE service_name = 'speech-processor'
AND timestamp > NOW() - INTERVAL '1 hour';

-- 4. Apply optimization
UPDATE pipeline_consumer_configs
SET
  max_poll_records = 5,  -- Process fewer messages at once
  max_poll_interval_ms = 900000  -- Allow 15 minutes for processing
WHERE service_name = 'speech-processor';

-- 5. Monitor improvement
SELECT * FROM v_consumer_performance_monitor
WHERE service_name = 'speech-processor';
```

## Integration with Existing Services

To integrate with your existing Docker containers:

1. Update your service to use the configuration loader
2. No changes needed to Docker containers or pipeline definitions
3. The loader will automatically apply optimized settings
4. Monitor performance and adjust as needed

The system is designed to work with your existing architecture while providing the optimization layer needed to handle high data volumes efficiently.
