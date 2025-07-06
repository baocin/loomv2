"""Kafka consumer configuration loader from database.

This module provides functionality to load optimized Kafka consumer configurations
from the TimescaleDB pipeline_consumer_configs table, similar to the TypeScript
implementation in pipeline-monitor-api.
"""

import json
from dataclasses import dataclass
from typing import List, Optional

import asyncpg
import structlog
from aiokafka import AIOKafkaConsumer
from cachetools import TTLCache

logger = structlog.get_logger(__name__)


@dataclass
class ConsumerConfiguration:
    """Kafka consumer configuration loaded from database."""

    service_name: str
    consumer_group_id: str
    max_poll_records: int = 100
    session_timeout_ms: int = 60000
    max_poll_interval_ms: int = 300000
    heartbeat_interval_ms: int = 20000
    partition_assignment_strategy: str = "range"
    enable_auto_commit: bool = False
    auto_commit_interval_ms: int = 5000
    auto_offset_reset: str = "earliest"
    fetch_min_bytes: int = 1
    fetch_max_wait_ms: int = 500
    max_partition_fetch_bytes: int = 1048576  # 1MB
    request_timeout_ms: int = 305000
    retry_backoff_ms: int = 100
    reconnect_backoff_ms: int = 50
    reconnect_backoff_max_ms: int = 1000


@dataclass
class ProcessingRecommendation:
    """Processing optimization recommendation."""

    service_name: str
    current_config: str
    recommended_config: str
    reason: str
    priority: str


class KafkaConsumerConfigLoader:
    """Loads and manages Kafka consumer configurations from database."""

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize the config loader.

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        # Cache configs for 5 minutes
        self._config_cache = TTLCache(maxsize=100, ttl=300)

    async def load_config(self, service_name: str) -> Optional[ConsumerConfiguration]:
        """Load consumer configuration for a specific service.

        Args:
            service_name: Name of the service to load config for

        Returns:
            ConsumerConfiguration if found, None otherwise
        """
        # Check cache first
        if service_name in self._config_cache:
            return self._config_cache[service_name]

        try:
            query = """
                SELECT
                    service_name,
                    consumer_group_id,
                    max_poll_records,
                    session_timeout_ms,
                    max_poll_interval_ms,
                    heartbeat_interval_ms,
                    partition_assignment_strategy,
                    enable_auto_commit,
                    auto_commit_interval_ms,
                    auto_offset_reset,
                    fetch_min_bytes,
                    fetch_max_wait_ms,
                    max_partition_fetch_bytes,
                    request_timeout_ms,
                    retry_backoff_ms,
                    reconnect_backoff_ms,
                    reconnect_backoff_max_ms
                FROM pipeline_consumer_configs
                WHERE service_name = $1
            """

            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, service_name)

            if not row:
                logger.warning(
                    "No consumer config found for service", service_name=service_name
                )
                return None

            config = ConsumerConfiguration(**dict(row))
            self._config_cache[service_name] = config

            logger.info(
                "Loaded consumer configuration",
                service_name=service_name,
                max_poll_records=config.max_poll_records,
                session_timeout_ms=config.session_timeout_ms,
            )

            return config

        except Exception as e:
            logger.error(
                "Error loading consumer config", service_name=service_name, error=str(e)
            )
            return None

    async def create_consumer(
        self,
        service_name: str,
        topics: List[str],
        kafka_bootstrap_servers: str,
        group_id: Optional[str] = None,
        **kwargs,
    ) -> AIOKafkaConsumer:
        """Create an optimized Kafka consumer for a service.

        Args:
            service_name: Name of the service
            topics: List of topics to subscribe to
            kafka_bootstrap_servers: Kafka bootstrap servers
            group_id: Optional consumer group ID (uses config if not provided)
            **kwargs: Additional consumer configuration options

        Returns:
            Configured AIOKafkaConsumer instance
        """
        config = await self.load_config(service_name)

        if config:
            # Use database configuration
            consumer_config = {
                "bootstrap_servers": kafka_bootstrap_servers,
                "group_id": group_id or config.consumer_group_id,
                "auto_offset_reset": config.auto_offset_reset,
                "enable_auto_commit": config.enable_auto_commit,
                "auto_commit_interval_ms": config.auto_commit_interval_ms,
                "session_timeout_ms": config.session_timeout_ms,
                "heartbeat_interval_ms": config.heartbeat_interval_ms,
                "max_poll_interval_ms": config.max_poll_interval_ms,
                "max_poll_records": config.max_poll_records,
                "fetch_min_bytes": config.fetch_min_bytes,
                "fetch_max_wait_ms": config.fetch_max_wait_ms,
                "max_partition_fetch_bytes": config.max_partition_fetch_bytes,
                "request_timeout_ms": config.request_timeout_ms,
                "retry_backoff_ms": config.retry_backoff_ms,
                "reconnect_backoff_ms": config.reconnect_backoff_ms,
                "reconnect_backoff_max_ms": config.reconnect_backoff_max_ms,
                "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
            }

            # Apply any overrides from kwargs
            consumer_config.update(kwargs)

            logger.info(
                "Creating optimized consumer",
                service_name=service_name,
                topics=topics,
                max_poll_records=config.max_poll_records,
                session_timeout_ms=config.session_timeout_ms,
            )
        else:
            # Use default configuration
            logger.warning(
                "Using default consumer configuration", service_name=service_name
            )
            consumer_config = {
                "bootstrap_servers": kafka_bootstrap_servers,
                "group_id": group_id or f"{service_name}-consumer-group",
                "auto_offset_reset": "earliest",
                "enable_auto_commit": False,
                "session_timeout_ms": 60000,
                "heartbeat_interval_ms": 20000,
                "max_poll_interval_ms": 300000,
                "max_poll_records": 100,
                "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
            }
            consumer_config.update(kwargs)

        # Create consumer with topics
        consumer = AIOKafkaConsumer(*topics, **consumer_config)

        return consumer

    async def get_processing_recommendations(self) -> List[ProcessingRecommendation]:
        """Get processing optimization recommendations based on metrics.

        Returns:
            List of processing recommendations
        """
        try:
            query = """
                WITH consumer_stats AS (
                    SELECT
                        h.service_name,
                        AVG(h.lag) as avg_lag,
                        MAX(h.lag) as max_lag,
                        COUNT(*) as measurement_count
                    FROM consumer_lag_history h
                    WHERE h.timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY h.service_name
                ),
                processing_stats AS (
                    SELECT
                        m.service_name,
                        AVG(m.messages_per_second) as avg_throughput,
                        AVG(m.processing_time_ms) as avg_processing_time
                    FROM consumer_processing_metrics m
                    WHERE m.timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY m.service_name
                )
                SELECT
                    c.service_name,
                    c.max_poll_records,
                    c.session_timeout_ms,
                    cs.avg_lag,
                    cs.max_lag,
                    ps.avg_throughput,
                    ps.avg_processing_time,
                    CASE
                        WHEN cs.avg_lag > 1000 AND c.max_poll_records < 100
                            THEN 'Increase max_poll_records to reduce lag'
                        WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8
                            THEN 'Increase session timeout to prevent rebalances'
                        WHEN cs.avg_lag < 10 AND c.max_poll_records > 100
                            THEN 'Decrease max_poll_records to reduce latency'
                        ELSE 'Configuration optimal'
                    END as recommendation,
                    CASE
                        WHEN cs.avg_lag > 1000 THEN 'high'
                        WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8 THEN 'high'
                        WHEN cs.avg_lag > 100 THEN 'medium'
                        ELSE 'low'
                    END as priority
                FROM pipeline_consumer_configs c
                LEFT JOIN consumer_stats cs ON c.service_name = cs.service_name
                LEFT JOIN processing_stats ps ON c.service_name = ps.service_name
                WHERE cs.service_name IS NOT NULL
                    AND (cs.avg_lag > 100 OR ps.avg_processing_time > c.session_timeout_ms * 0.5)
                ORDER BY
                    CASE
                        WHEN cs.avg_lag > 1000 THEN 1
                        WHEN ps.avg_processing_time > c.session_timeout_ms * 0.8 THEN 2
                        ELSE 3
                    END
            """

            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query)

            recommendations = []
            for row in rows:
                rec = ProcessingRecommendation(
                    service_name=row["service_name"],
                    current_config=f"max_poll_records: {row['max_poll_records']}, "
                    f"session_timeout: {row['session_timeout_ms']}",
                    recommended_config=row["recommendation"],
                    reason=f"Avg lag: {int(row['avg_lag'] or 0)}, "
                    f"Avg processing time: {int(row['avg_processing_time'] or 0)}ms",
                    priority=row["priority"],
                )
                recommendations.append(rec)

            return recommendations

        except Exception as e:
            logger.error("Error getting processing recommendations", error=str(e))
            return []

    async def record_consumer_lag(
        self, service_name: str, topic: str, partition: int, lag: int, offset: int
    ) -> None:
        """Record consumer lag metrics.

        Args:
            service_name: Name of the service
            topic: Kafka topic
            partition: Partition number
            lag: Current lag
            offset: Current consumer offset
        """
        try:
            query = """
                INSERT INTO consumer_lag_history
                (service_name, topic, partition, lag, consumer_offset)
                VALUES ($1, $2, $3, $4, $5)
            """

            async with self.db_pool.acquire() as conn:
                await conn.execute(query, service_name, topic, partition, lag, offset)

        except Exception as e:
            logger.error(
                "Error recording consumer lag", service_name=service_name, error=str(e)
            )

    async def record_processing_metrics(
        self,
        service_name: str,
        messages_processed: int,
        processing_time_ms: float,
        memory_usage_mb: float,
    ) -> None:
        """Record processing performance metrics.

        Args:
            service_name: Name of the service
            messages_processed: Number of messages processed
            processing_time_ms: Total processing time in milliseconds
            memory_usage_mb: Memory usage in MB
        """
        try:
            messages_per_second = (
                (messages_processed / processing_time_ms) * 1000
                if processing_time_ms > 0
                else 0
            )

            query = """
                INSERT INTO consumer_processing_metrics
                (service_name, messages_processed, processing_time_ms,
                 messages_per_second, memory_usage_mb)
                VALUES ($1, $2, $3, $4, $5)
            """

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    query,
                    service_name,
                    messages_processed,
                    processing_time_ms,
                    messages_per_second,
                    memory_usage_mb,
                )

        except Exception as e:
            logger.error(
                "Error recording processing metrics",
                service_name=service_name,
                error=str(e),
            )


async def create_optimized_consumer(
    db_pool: asyncpg.Pool,
    service_name: str,
    topics: List[str],
    kafka_bootstrap_servers: str,
    group_id: Optional[str] = None,
    **kwargs,
) -> AIOKafkaConsumer:
    """Helper function to create an optimized consumer.

    Args:
        db_pool: Database connection pool
        service_name: Name of the service
        topics: List of topics to subscribe to
        kafka_bootstrap_servers: Kafka bootstrap servers
        group_id: Optional consumer group ID
        **kwargs: Additional consumer configuration

    Returns:
        Configured AIOKafkaConsumer instance
    """
    loader = KafkaConsumerConfigLoader(db_pool)
    return await loader.create_consumer(
        service_name, topics, kafka_bootstrap_servers, group_id, **kwargs
    )
