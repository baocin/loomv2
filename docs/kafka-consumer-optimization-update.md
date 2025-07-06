# Kafka Consumer Optimization Update

## Summary

Updated Kafka consumer implementations in key services to use the optimization loader from `loom-common`. This enables dynamic consumer configuration loading from the database, automatic performance metrics collection, and lag monitoring.

## Services Updated

### 1. silero-vad (Voice Activity Detection)
- **File**: `services/silero-vad/app/kafka_consumer.py`
- **Changes**:
  - Added database connection pool initialization
  - Integrated `KafkaConsumerConfigLoader` for optimized consumer creation
  - Added periodic metrics recording (processing metrics and consumer lag)
  - Updated config to include database settings
  - Added dependencies: asyncpg, psutil, loom-common

### 2. minicpm-vision (Vision Processing)
- **File**: `services/minicpm-vision/app/kafka_consumer.py`
- **Changes**:
  - Added database URL parameter to consumer initialization
  - Integrated config loader with fallback to default consumer
  - Added metrics recording functionality
  - Updated main.py to pass database configuration
  - Added dependencies: asyncpg, psutil, loom-common

### 3. kyutai-stt (Speech-to-Text)
- **File**: `services/kyutai-stt/app/kafka_consumer.py`
- **Changes**:
  - Added database pool and config loader
  - Replaced manual consumer creation with optimized version
  - Added periodic metrics recording
  - Updated config to include database settings
  - Added dependencies: asyncpg, psutil, loom-common

## Key Features Added

1. **Dynamic Configuration Loading**
   - Services now load optimized Kafka consumer configurations from the `pipeline_consumer_configs` table
   - Configurations are cached for 5 minutes to reduce database load

2. **Performance Metrics Collection**
   - Automatic recording of:
     - Messages processed
     - Processing time
     - Memory usage
     - Consumer lag per partition
   - Metrics stored in TimescaleDB tables for analysis

3. **Fallback Support**
   - Services maintain backward compatibility
   - If no database configuration is found, default settings are used

## Configuration Pattern

Each service now includes:
```python
# Database settings
database_url: str = "postgresql://loom:loom@postgres:5432/loom"
database_pool_min_size: int = 2
database_pool_max_size: int = 10
```

## Consumer Initialization Pattern

```python
# Create database pool
self.db_pool = await asyncpg.create_pool(
    settings.database_url,
    min_size=settings.database_pool_min_size,
    max_size=settings.database_pool_max_size,
)

# Create config loader
self.config_loader = KafkaConsumerConfigLoader(self.db_pool)

# Create optimized consumer
self.consumer = await self.config_loader.create_consumer(
    service_name=settings.service_name,
    topics=[settings.kafka_input_topic],
    kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
    group_id=settings.kafka_consumer_group,
)
```

## Metrics Recording Pattern

```python
async def _maybe_record_metrics(self):
    """Record processing metrics periodically."""
    if time_since_last_metrics >= self._metrics_interval and self.config_loader:
        # Record processing metrics
        await self.config_loader.record_processing_metrics(...)

        # Record consumer lag
        for tp in partitions:
            await self.config_loader.record_consumer_lag(...)
```

## Next Steps

Additional services that could benefit from optimization:
- face-emotion
- gemma3n-processor
- moondream-station
- text-embedder
- nomic-embed
- onefilellm

These services can be updated following the same pattern established in the three services updated above.
