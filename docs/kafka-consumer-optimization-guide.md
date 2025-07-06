# Kafka Consumer Optimization Guide

## Overview

This guide explains how to update Kafka consumers in the Loom v2 pipeline to use the database-driven optimization loader. This system automatically configures consumer parameters based on service characteristics to optimize throughput and reliability.

## Benefits

1. **Automatic Optimization**: Consumer settings are tuned based on service type (e.g., GPU-intensive vision models get longer timeouts)
2. **Centralized Configuration**: All consumer configs managed in one place via database
3. **Performance Monitoring**: Built-in lag tracking and processing metrics
4. **Dynamic Tuning**: Configurations can be updated without code changes

## Migration Steps

### 1. For Services Using BaseKafkaConsumer

If your service already extends `BaseKafkaConsumer` from `loom-common`, update the initialization:

```python
# Before
class MyConsumer(BaseKafkaConsumer):
    def __init__(self, settings):
        super().__init__(
            settings=settings,
            topics=["my.input.topic"],
            group_id="my-consumer-group"
        )

# After
class MyConsumer(BaseKafkaConsumer):
    def __init__(self, settings, db_pool):
        super().__init__(
            settings=settings,
            topics=["my.input.topic"],
            group_id="my-consumer-group",
            db_pool=db_pool,  # Add database pool
            service_name="my-service"  # Add service name
        )
```

### 2. For Services Using AIOKafkaConsumer Directly

Replace direct consumer creation with the optimization loader:

```python
# Before
from aiokafka import AIOKafkaConsumer

async def create_consumer():
    consumer = AIOKafkaConsumer(
        "my.topic",
        bootstrap_servers="localhost:9092",
        group_id="my-group",
        max_poll_records=100,
        session_timeout_ms=30000
    )
    await consumer.start()
    return consumer

# After
from loom_common.kafka import create_optimized_consumer
import asyncpg

async def create_consumer():
    # Create database pool
    db_pool = await asyncpg.create_pool(
        "postgresql://loom:loom@localhost:5432/loom"
    )

    # Create optimized consumer
    consumer = await create_optimized_consumer(
        db_pool=db_pool,
        service_name="my-service",
        topics=["my.topic"],
        kafka_bootstrap_servers="localhost:9092"
    )
    await consumer.start()
    return consumer
```

### 3. For Services Using kafka-python (Synchronous)

For synchronous consumers, you'll need to convert to async or create a wrapper:

```python
# Example async wrapper for sync services
import asyncio
from loom_common.kafka import KafkaConsumerConfigLoader

class OptimizedSyncConsumer:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.config = None

    def load_config(self):
        """Load config synchronously"""
        async def _load():
            db_pool = await asyncpg.create_pool(DATABASE_URL)
            loader = KafkaConsumerConfigLoader(db_pool)
            config = await loader.load_config(self.service_name)
            await db_pool.close()
            return config

        self.config = asyncio.run(_load())

    def create_consumer(self):
        """Create consumer with loaded config"""
        if not self.config:
            self.load_config()

        from kafka import KafkaConsumer

        return KafkaConsumer(
            "my.topic",
            bootstrap_servers="localhost:9092",
            group_id=self.config.consumer_group_id if self.config else "default-group",
            max_poll_records=self.config.max_poll_records if self.config else 100,
            session_timeout_ms=self.config.session_timeout_ms if self.config else 30000,
            # ... other settings from config
        )
```

## Service Configuration Examples

### High-Volume Simple Processing (e.g., VAD, sensor aggregation)
```sql
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records,
    session_timeout_ms, max_poll_interval_ms
) VALUES (
    'my-vad-service', 'loom-vad', 500, 30000, 60000
);
```

### GPU-Intensive Processing (e.g., vision models, STT)
```sql
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records,
    session_timeout_ms, max_poll_interval_ms, max_partition_fetch_bytes
) VALUES (
    'my-vision-service', 'loom-vision', 1, 300000, 600000, 52428800
);
```

### Network I/O Bound (e.g., geocoding, external APIs)
```sql
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records,
    session_timeout_ms, retry_backoff_ms
) VALUES (
    'my-geocoder', 'loom-geocoder', 10, 120000, 1000
);
```

## Monitoring Consumer Performance

### View Current Lag
```sql
SELECT * FROM v_current_consumer_lag
WHERE service_name = 'my-service';
```

### Check for Alerts
```sql
SELECT * FROM v_consumer_lag_alerts
WHERE alert_level != 'ok';
```

### View Processing Metrics
```sql
SELECT
    service_name,
    AVG(messages_per_second) as avg_throughput,
    AVG(processing_time_ms) as avg_processing_time,
    MAX(memory_usage_mb) as peak_memory
FROM consumer_processing_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY service_name;
```

### Get Optimization Recommendations
```python
from loom_common.kafka import KafkaConsumerConfigLoader

async def check_recommendations():
    loader = KafkaConsumerConfigLoader(db_pool)
    recommendations = await loader.get_processing_recommendations()

    for rec in recommendations:
        if rec.priority == "high":
            print(f"{rec.service_name}: {rec.recommended_config}")
            print(f"Reason: {rec.reason}")
```

## Testing Your Migration

1. **Start with Default Config**: The system falls back to defaults if no config exists
2. **Monitor Metrics**: Watch lag and processing time after deployment
3. **Tune Gradually**: Adjust `max_poll_records` based on processing capacity
4. **Use Monitoring Views**: Check `v_consumer_config_monitoring` for config effectiveness

## Common Issues and Solutions

### Issue: Consumer rebalancing frequently
**Solution**: Increase `session_timeout_ms` and `max_poll_interval_ms`

### Issue: High memory usage
**Solution**: Decrease `max_poll_records` and `max_partition_fetch_bytes`

### Issue: Consumer lag increasing
**Solution**: Increase `max_poll_records` or scale horizontally (add replicas)

### Issue: Messages timing out
**Solution**: Increase `max_poll_interval_ms` for slow processors

## Required Database Migrations

Ensure these migrations are applied:
- `038_add_consumer_configurations.sql` - Consumer config tables
- `041_add_consumer_metrics_tables.sql` - Metrics and monitoring tables

## Example: Complete Migration

Here's a complete example migrating the georegion-detector service:

```python
# georegion_consumer.py
import asyncio
import asyncpg
from loom_common.kafka import BaseKafkaConsumer
from aiokafka import ConsumerRecord

class GeoregionConsumer(BaseKafkaConsumer):
    def __init__(self, settings, db_pool):
        super().__init__(
            settings=settings,
            topics=["location.address.geocoded"],
            group_id="loom-georegion",
            db_pool=db_pool,
            service_name="georegion-detector"
        )
        self.detector = GeoregionDetector()

    async def process_message(self, message: ConsumerRecord):
        """Process geocoded location"""
        location = GeocodedLocation(**message.value)

        # Detect georegions
        detections = await self.detector.detect(location)

        # Send results
        for detection in detections:
            await self.send_to_topic(
                "location.georegion.detected",
                detection.model_dump()
            )

        # Metrics are automatically recorded by base class

# main.py
async def main():
    # Create database pool
    db_pool = await asyncpg.create_pool(settings.database_url)

    # Create consumer with optimization
    consumer = GeoregionConsumer(settings, db_pool)

    # Start and run
    await consumer.start()
    await consumer.run()
```

## Next Steps

1. Identify services with performance issues
2. Add their configurations to `pipeline_consumer_configs`
3. Update service code to use optimization loader
4. Monitor metrics and adjust configurations
5. Set up alerts based on `v_consumer_lag_alerts`
