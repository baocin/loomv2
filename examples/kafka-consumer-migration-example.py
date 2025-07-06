"""
Example: Migrating a Kafka Consumer to Use Database-Driven Optimization

This example shows how to migrate the kyutai-stt service to use the
optimization loader for better performance configuration.
"""

# ============================================================================
# BEFORE: Original consumer with hardcoded settings
# ============================================================================

# File: services/kyutai-stt/app/kafka_consumer_old.py

import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from app.config import settings


class KafkaConsumer:
    """Original consumer with hardcoded settings"""

    def __init__(self):
        self.consumer = None
        self.producer = None

    async def start(self):
        # Hardcoded consumer settings - not optimal for GPU-intensive STT
        self.consumer = AIOKafkaConsumer(
            settings.kafka_input_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            session_timeout_ms=settings.kafka_session_timeout_ms,  # 30000
            heartbeat_interval_ms=settings.kafka_heartbeat_interval_ms,  # 10000
            max_poll_records=settings.kafka_max_poll_records,  # 10
        )

        await self.consumer.start()


# ============================================================================
# AFTER: Migrated consumer using optimization loader
# ============================================================================

# File: services/kyutai-stt/app/kafka_consumer_new.py

import asyncpg
from loom_common.kafka import BaseKafkaConsumer
from app.models import AudioChunk, TranscribedText
from app.kyutai_streaming_processor import KyutaiStreamingProcessor


# Option 1: Using BaseKafkaConsumer (Recommended)
class OptimizedKafkaConsumer(BaseKafkaConsumer):
    """Consumer that extends BaseKafkaConsumer for automatic optimization"""

    def __init__(self, settings, db_pool):
        super().__init__(
            settings=settings,
            topics=[settings.kafka_input_topic],
            group_id=settings.kafka_consumer_group,
            db_pool=db_pool,  # Pass database pool
            service_name="kyutai-stt",  # Service name for config lookup
        )
        self.asr_processor = KyutaiStreamingProcessor()

    async def process_message(self, message):
        """Process a single audio message"""
        try:
            # Parse message
            audio_chunk = AudioChunk(**message.value)

            # Decode and process audio
            audio_bytes = audio_chunk.decode_audio()

            # Run STT (this is slow, hence we need optimized timeouts)
            async for word in self.asr_processor.process_audio_async(
                audio_bytes, audio_chunk.sample_rate, audio_chunk.channels
            ):
                # Create transcript
                transcript = TranscribedText(
                    device_id=audio_chunk.device_id,
                    recorded_at=audio_chunk.recorded_at,
                    timestamp=audio_chunk.timestamp,
                    message_id=f"{audio_chunk.message_id}_word_{word['index']}",
                    trace_id=audio_chunk.trace_id,
                    services_encountered=audio_chunk.services_encountered
                    + ["kyutai-stt"],
                    text=word["text"],
                    confidence=word["confidence"],
                    start_time_ms=word["start_ms"],
                    end_time_ms=word["end_ms"],
                    is_final=True,
                    language="en",
                )

                # Send to output topic
                await self.send_to_topic(
                    settings.kafka_output_topic,
                    transcript.model_dump(mode="json"),
                    key=audio_chunk.device_id,
                )

        except Exception as e:
            logger.error("Error processing message", error=str(e))
            raise  # Let base class handle DLQ


# Option 2: Direct usage with config loader
from loom_common.kafka import create_optimized_consumer


class DirectOptimizedConsumer:
    """Direct usage of optimization loader without base class"""

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.db_pool = None

    async def start(self):
        # Create database pool
        self.db_pool = await asyncpg.create_pool(
            settings.database_url, min_size=2, max_size=10
        )

        # Create optimized consumer
        # This will load settings from pipeline_consumer_configs table
        self.consumer = await create_optimized_consumer(
            db_pool=self.db_pool,
            service_name="kyutai-stt",
            topics=[settings.kafka_input_topic],
            kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
        )

        # The consumer is now configured with:
        # - max_poll_records: 10 (for GPU-intensive processing)
        # - session_timeout_ms: 120000 (2 min for slow processing)
        # - max_poll_interval_ms: 300000 (5 min)
        # - max_partition_fetch_bytes: 10485760 (10MB for audio)

        await self.consumer.start()

        # Create producer separately
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self.producer.start()


# ============================================================================
# Main application integration
# ============================================================================

# File: services/kyutai-stt/app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI

# Global instances
kafka_consumer = None
consumer_task = None
db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler with database pool"""
    global kafka_consumer, consumer_task, db_pool

    # Startup
    logger.info("Starting Kyutai-STT service", version=settings.version)

    # Create database pool for optimization loader
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)

    # Create and start optimized consumer
    kafka_consumer = OptimizedKafkaConsumer(settings, db_pool)
    await kafka_consumer.start()

    # Start consumer task
    consumer_task = asyncio.create_task(kafka_consumer.run())

    logger.info("Kyutai-STT service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Kyutai-STT service")

    if kafka_consumer:
        await kafka_consumer.stop()

    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass

    if db_pool:
        await db_pool.close()

    logger.info("Kyutai-STT service stopped")


# Create FastAPI app
app = FastAPI(
    title="Kyutai STT Service",
    description="Speech-to-text processing using Kyutai models with optimized Kafka consumption",
    version=settings.version,
    lifespan=lifespan,
)


# ============================================================================
# Configuration in Database
# ============================================================================

"""
The consumer configuration is stored in the database and can be updated without
code changes. For the kyutai-stt service:

INSERT INTO pipeline_consumer_configs (
    service_name,
    consumer_group_id,
    max_poll_records,
    session_timeout_ms,
    max_poll_interval_ms,
    heartbeat_interval_ms,
    max_partition_fetch_bytes,
    partition_assignment_strategy
) VALUES (
    'kyutai-stt',
    'loom-kyutai-stt',
    10,  -- Process 10 audio chunks at a time
    120000,  -- 2 minute session timeout
    300000,  -- 5 minute max poll interval for GPU processing
    40000,   -- Heartbeat every 40 seconds
    10485760,  -- 10MB max fetch size for audio
    'sticky'   -- Keep partitions assigned to same consumer
) ON CONFLICT (service_name)
DO UPDATE SET
    max_poll_records = EXCLUDED.max_poll_records,
    session_timeout_ms = EXCLUDED.session_timeout_ms,
    max_poll_interval_ms = EXCLUDED.max_poll_interval_ms;
"""


# ============================================================================
# Monitoring the Optimized Consumer
# ============================================================================

"""
After deployment, monitor the consumer performance:

-- Check current lag
SELECT * FROM v_current_consumer_lag
WHERE service_name = 'kyutai-stt';

-- View processing metrics
SELECT
    AVG(messages_per_second) as avg_throughput,
    AVG(processing_time_ms) as avg_processing_time,
    MAX(memory_usage_mb) as peak_memory
FROM consumer_processing_hourly
WHERE service_name = 'kyutai-stt'
  AND hour > NOW() - INTERVAL '24 hours';

-- Get optimization recommendations
SELECT * FROM v_consumer_lag_alerts
WHERE service_name = 'kyutai-stt';
"""


# ============================================================================
# Benefits of Migration
# ============================================================================

"""
1. AUTOMATIC TUNING: The consumer gets optimal settings for STT workload
   - Longer timeouts prevent rebalancing during GPU processing
   - Appropriate batch sizes for audio processing

2. CENTRALIZED CONFIG: All consumer settings in one place
   - Change timeouts without redeploying
   - A/B test different configurations

3. BUILT-IN MONITORING: Performance metrics collected automatically
   - Consumer lag tracked per partition
   - Processing time and throughput measured
   - Memory usage monitored

4. DYNAMIC OPTIMIZATION: Get recommendations based on actual performance
   - System suggests config changes when lag increases
   - Alerts when consumers are struggling

5. FALLBACK SAFETY: If DB is unavailable, falls back to defaults
   - Service continues to work even if optimization fails
   - Gradual migration path
"""
