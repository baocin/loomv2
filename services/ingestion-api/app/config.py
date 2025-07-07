"""Configuration management for the ingestion API service."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers",
    )
    kafka_client_id: str = Field(
        default="loom-ingestion-api",
        description="Kafka client ID",
    )
    kafka_compression_type: str = Field(
        default="none",
        description="Kafka message compression",
    )

    # Kafka topic management
    kafka_auto_create_topics: bool = Field(
        default=True,
        description="Automatically create required topics on startup",
    )
    kafka_default_partitions: int = Field(
        default=3,
        description="Default number of partitions for new topics",
    )
    kafka_default_replication_factor: int = Field(
        default=1,
        description="Default replication factor for new topics",
    )

    # Topics - Audio
    topic_device_audio_raw: str = Field(
        default="device.audio.raw",
        description="Topic for raw audio chunks",
    )

    # Topics - Sensors
    topic_device_sensor_raw: str = Field(
        default="device.sensor.{sensor_type}.raw",
        description="Topic pattern for sensor data",
    )

    # Topics - Images
    topic_device_image_raw: str = Field(
        default="device.image.camera.raw",
        description="Topic for camera images",
    )

    # Topics - System Apps (Sprint 4)
    topic_device_system_apps_macos: str = Field(
        default="device.system.apps.macos.raw",
        description="Topic for macOS app monitoring data",
    )
    topic_device_system_apps_android: str = Field(
        default="device.system.apps.android.raw",
        description="Topic for Android app monitoring data",
    )

    # Topics - Device Metadata (Sprint 4)
    topic_device_metadata: str = Field(
        default="device.metadata.raw",
        description="Topic for arbitrary device metadata",
    )

    # Topics - Device State
    topic_device_state_lock: str = Field(
        default="device.state.lock.raw",
        description="Topic for device lock/unlock state",
    )

    # App Monitoring Configuration
    app_monitoring_enabled: bool = Field(
        default=True,
        description="Enable app monitoring endpoints",
    )
    app_monitoring_max_apps_per_request: int = Field(
        default=100,
        description="Maximum number of apps per monitoring request",
    )

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8001, description="Prometheus metrics port")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    model_config = {
        "env_prefix": "LOOM_",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()
