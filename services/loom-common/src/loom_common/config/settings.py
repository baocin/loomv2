"""
Base settings class with common configuration for all Loom v2 services
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings as PydanticBaseSettings


class BaseSettings(PydanticBaseSettings):
    """Base configuration for all Loom v2 services"""

    # Service identification
    service_name: str = Field(
        default="loom-service",
        env="LOOM_SERVICE_NAME",
        description="Name of the service for logging and metrics",
    )
    environment: str = Field(
        default="development",
        env="LOOM_ENVIRONMENT",
        description="Deployment environment",
    )

    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        env="LOOM_KAFKA_BOOTSTRAP_SERVERS",
        description="Kafka broker addresses",
    )
    kafka_topic_prefix: str = Field(
        default="",
        env="LOOM_KAFKA_TOPIC_PREFIX",
        description="Prefix for all Kafka topics",
    )
    kafka_consumer_group_prefix: str = Field(
        default="",
        env="LOOM_KAFKA_CONSUMER_GROUP_PREFIX",
        description="Prefix for consumer groups",
    )

    # Database configuration
    database_url: Optional[str] = Field(
        default=None,
        env="LOOM_DATABASE_URL",
        description="PostgreSQL/TimescaleDB connection URL",
    )

    # Logging configuration
    log_level: str = Field(
        default="INFO", env="LOOM_LOG_LEVEL", description="Logging level"
    )
    log_format: str = Field(
        default="json", env="LOOM_LOG_FORMAT", description="Log format: json or text"
    )

    # Health check configuration
    health_check_enabled: bool = Field(
        default=True,
        env="LOOM_HEALTH_CHECK_ENABLED",
        description="Enable health check endpoints",
    )
    health_check_port: int = Field(
        default=8000,
        env="LOOM_HEALTH_CHECK_PORT",
        description="Port for health check endpoints",
    )

    # Metrics configuration
    metrics_enabled: bool = Field(
        default=True,
        env="LOOM_METRICS_ENABLED",
        description="Enable Prometheus metrics",
    )
    metrics_port: int = Field(
        default=9090, env="LOOM_METRICS_PORT", description="Port for metrics endpoint"
    )

    # Tracing configuration
    trace_enabled: bool = Field(
        default=False,
        env="LOOM_TRACE_ENABLED",
        description="Enable distributed tracing",
    )
    trace_endpoint: Optional[str] = Field(
        default=None,
        env="LOOM_TRACE_ENDPOINT",
        description="OpenTelemetry collector endpoint",
    )

    # Development settings
    debug: bool = Field(
        default=False, env="LOOM_DEBUG", description="Enable debug mode"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_kafka_topic(self, topic_name: str) -> str:
        """Get full Kafka topic name with prefix"""
        if self.kafka_topic_prefix:
            return f"{self.kafka_topic_prefix}.{topic_name}"
        return topic_name

    def get_consumer_group(self, group_name: str) -> str:
        """Get full consumer group name with prefix"""
        if self.kafka_consumer_group_prefix:
            return f"{self.kafka_consumer_group_prefix}.{group_name}"
        return group_name
