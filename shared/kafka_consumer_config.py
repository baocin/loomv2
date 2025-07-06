#!/usr/bin/env python3
"""
Kafka Consumer Configuration Loader for Loom v2 Services

This module provides utilities to load optimized Kafka consumer configurations
from the TimescaleDB database based on service characteristics.
"""

import os
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from confluent_kafka import Consumer

logger = logging.getLogger(__name__)


@dataclass
class ConsumerConfig:
    """Kafka consumer configuration parameters"""

    service_name: str
    consumer_group_id: str
    max_poll_records: int
    session_timeout_ms: int
    max_poll_interval_ms: int
    heartbeat_interval_ms: int
    partition_assignment_strategy: str
    enable_auto_commit: bool
    auto_commit_interval_ms: int
    auto_offset_reset: str
    fetch_min_bytes: int
    fetch_max_wait_ms: int
    max_partition_fetch_bytes: int
    request_timeout_ms: int
    retry_backoff_ms: int
    reconnect_backoff_ms: int
    reconnect_backoff_max_ms: int


class KafkaConsumerConfigLoader:
    """Load and manage Kafka consumer configurations from database"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize the config loader

        Args:
            database_url: PostgreSQL connection string. If not provided,
                         will use LOOM_DATABASE_URL environment variable
        """
        self.database_url = database_url or os.getenv(
            "LOOM_DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom"
        )

    def _get_connection(self):
        """Create a database connection"""
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def load_config(self, service_name: str) -> Optional[ConsumerConfig]:
        """
        Load consumer configuration for a specific service

        Args:
            service_name: Name of the service to load config for

        Returns:
            ConsumerConfig object or None if not found
        """
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
            WHERE service_name = %s
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (service_name,))
                    row = cur.fetchone()

                    if not row:
                        logger.warning(
                            f"No consumer configuration found for service: {service_name}"
                        )
                        return None

                    return ConsumerConfig(**row)

        except Exception as e:
            logger.error(f"Failed to load consumer config for {service_name}: {e}")
            raise

    def get_kafka_config(
        self,
        service_name: str,
        bootstrap_servers: Optional[str] = None,
        additional_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get Kafka consumer configuration in confluent-kafka format

        Args:
            service_name: Name of the service
            bootstrap_servers: Kafka bootstrap servers (default from env)
            additional_config: Additional config to merge

        Returns:
            Dictionary of Kafka consumer configuration
        """
        config = self.load_config(service_name)

        if not config:
            # Return default configuration
            config = self._get_default_config(service_name)

        bootstrap_servers = bootstrap_servers or os.getenv(
            "LOOM_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )

        kafka_config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": config.consumer_group_id,
            "session.timeout.ms": config.session_timeout_ms,
            "max.poll.interval.ms": config.max_poll_interval_ms,
            "heartbeat.interval.ms": config.heartbeat_interval_ms,
            "enable.auto.commit": config.enable_auto_commit,
            "auto.commit.interval.ms": config.auto_commit_interval_ms,
            "auto.offset.reset": config.auto_offset_reset,
            "fetch.min.bytes": config.fetch_min_bytes,
            "fetch.wait.max.ms": config.fetch_max_wait_ms,
            "max.partition.fetch.bytes": config.max_partition_fetch_bytes,
            "request.timeout.ms": config.request_timeout_ms,
            "retry.backoff.ms": config.retry_backoff_ms,
            "reconnect.backoff.ms": config.reconnect_backoff_ms,
            "reconnect.backoff.max.ms": config.reconnect_backoff_max_ms,
            "partition.assignment.strategy": config.partition_assignment_strategy,
            # Custom property for batch size control
            "max.poll.records": config.max_poll_records,
        }

        # Add any additional configuration
        if additional_config:
            kafka_config.update(additional_config)

        return kafka_config

    def _get_default_config(self, service_name: str) -> ConsumerConfig:
        """Get default configuration if none exists in database"""
        return ConsumerConfig(
            service_name=service_name,
            consumer_group_id=f"loom-{service_name}",
            max_poll_records=100,
            session_timeout_ms=60000,
            max_poll_interval_ms=300000,
            heartbeat_interval_ms=20000,
            partition_assignment_strategy="range",
            enable_auto_commit=False,
            auto_commit_interval_ms=5000,
            auto_offset_reset="earliest",
            fetch_min_bytes=1,
            fetch_max_wait_ms=500,
            max_partition_fetch_bytes=1048576,  # 1MB
            request_timeout_ms=305000,
            retry_backoff_ms=100,
            reconnect_backoff_ms=50,
            reconnect_backoff_max_ms=1000,
        )

    def create_consumer(
        self,
        service_name: str,
        topics: List[str],
        bootstrap_servers: Optional[str] = None,
        additional_config: Optional[Dict[str, Any]] = None,
    ) -> Consumer:
        """
        Create a configured Kafka consumer instance

        Args:
            service_name: Name of the service
            topics: List of topics to subscribe to
            bootstrap_servers: Kafka bootstrap servers
            additional_config: Additional config options

        Returns:
            Configured Consumer instance
        """
        config = self.get_kafka_config(
            service_name, bootstrap_servers, additional_config
        )

        # Remove custom properties that aren't valid for confluent-kafka
        max_poll_records = config.pop("max.poll.records", 100)

        consumer = Consumer(config)
        consumer.subscribe(topics)

        # Store max_poll_records as an attribute for use in polling
        consumer.max_poll_records = max_poll_records

        logger.info(
            f"Created consumer for {service_name} with group {config['group.id']}"
        )
        logger.info(f"Subscribed to topics: {topics}")
        logger.info(f"Max poll records: {max_poll_records}")

        return consumer

    def get_processing_recommendations(self, service_name: str) -> Dict[str, Any]:
        """
        Get processing recommendations based on configuration

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with processing recommendations
        """
        config = self.load_config(service_name)
        if not config:
            config = self._get_default_config(service_name)

        return {
            "batch_size": config.max_poll_records,
            "max_processing_time_ms": config.max_poll_interval_ms
            - config.session_timeout_ms,
            "commit_strategy": "auto" if config.enable_auto_commit else "manual",
            "partition_strategy": config.partition_assignment_strategy,
            "recommendations": self._get_specific_recommendations(config),
        }

    def _get_specific_recommendations(self, config: ConsumerConfig) -> List[str]:
        """Generate specific recommendations based on configuration"""
        recommendations = []

        if config.max_poll_records == 1:
            recommendations.append(
                "Process messages one at a time - likely GPU/compute intensive"
            )
            recommendations.append(
                "Consider implementing result caching if processing similar data"
            )

        if config.max_poll_records > 500:
            recommendations.append(
                "High batch size - ensure batch processing is implemented"
            )
            recommendations.append("Monitor memory usage during peak loads")

        if config.max_poll_interval_ms > 600000:  # 10 minutes
            recommendations.append(
                "Long processing timeout - ensure proper error handling"
            )
            recommendations.append("Consider implementing processing checkpoints")

        if config.partition_assignment_strategy == "sticky":
            recommendations.append("Sticky partitions - good for stateful processing")
            recommendations.append("Implement proper state cleanup on rebalance")

        if not config.enable_auto_commit:
            recommendations.append(
                "Manual commit enabled - commit after successful processing"
            )
            recommendations.append(
                "Implement proper error recovery without message loss"
            )

        return recommendations


def poll_with_limit(consumer: Consumer, timeout_ms: int = 1000) -> List[Any]:
    """
    Poll messages with max_poll_records limit

    Args:
        consumer: Kafka consumer instance (must have max_poll_records attribute)
        timeout_ms: Poll timeout in milliseconds

    Returns:
        List of messages up to max_poll_records limit
    """
    max_records = getattr(consumer, "max_poll_records", 100)
    messages = []

    # Poll up to max_records messages
    while len(messages) < max_records:
        msg = consumer.poll(timeout_ms / max_records)
        if msg is None:
            break
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        messages.append(msg)

    return messages


# Example usage
if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python kafka_consumer_config.py <service_name>")
        sys.exit(1)

    service_name = sys.argv[1]
    loader = KafkaConsumerConfigLoader()

    # Load configuration
    config = loader.load_config(service_name)
    if config:
        print(f"\nConfiguration for {service_name}:")
        print(json.dumps(config.__dict__, indent=2))
    else:
        print(f"\nNo configuration found for {service_name}, using defaults")

    # Get Kafka config
    kafka_config = loader.get_kafka_config(service_name)
    print("\nKafka configuration:")
    print(json.dumps(kafka_config, indent=2))

    # Get recommendations
    recommendations = loader.get_processing_recommendations(service_name)
    print("\nProcessing recommendations:")
    print(json.dumps(recommendations, indent=2))
