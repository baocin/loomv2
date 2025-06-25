"""Configuration for VAD Processor Service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """VAD Processor configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="VAD_",
        env_file=".env",
        case_sensitive=False,
    )

    # Service identification
    service_name: str = Field(
        default="vad-processor",
        description="Service name for logging and metrics",
    )
    service_version: str = Field(
        default="0.1.0",
        description="Service version",
    )

    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers",
    )
    kafka_consumer_group: str = Field(
        default="vad-processor-group",
        description="Kafka consumer group ID",
    )
    kafka_input_topic: str = Field(
        default="device.audio.raw",
        description="Input topic for raw audio data",
    )
    kafka_output_topic: str = Field(
        default="media.audio.vad_filtered",
        description="Output topic for VAD-filtered audio",
    )

    # Database configuration
    database_url: str = Field(
        default="postgresql://loom:loom@localhost:5432/loom",
        description="PostgreSQL/TimescaleDB connection URL",
    )

    # VAD model configuration
    vad_model: str = Field(
        default="silero_vad",
        description="VAD model to use",
    )
    vad_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="VAD confidence threshold",
    )
    vad_min_speech_duration_ms: int = Field(
        default=250,
        ge=0,
        description="Minimum speech duration in milliseconds",
    )
    vad_max_speech_duration_ms: int = Field(
        default=30000,
        ge=0,
        description="Maximum speech duration in milliseconds",
    )
    vad_padding_duration_ms: int = Field(
        default=100,
        ge=0,
        description="Padding to add before/after speech segments",
    )

    # Processing configuration
    batch_size: int = Field(
        default=10,
        ge=1,
        description="Number of messages to process in batch",
    )
    processing_timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout for processing a single audio chunk",
    )

    # Monitoring
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics",
    )
    metrics_port: int = Field(
        default=8001,
        ge=1,
        le=65535,
        description="Port for Prometheus metrics endpoint",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )


settings = Settings()
