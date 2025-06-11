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
        description="Kafka bootstrap servers"
    )
    kafka_client_id: str = Field(
        default="loom-ingestion-api", 
        description="Kafka client ID"
    )
    kafka_compression_type: str = Field(
        default="lz4", 
        description="Kafka message compression"
    )
    
    # Topics
    topic_device_audio_raw: str = Field(
        default="device.audio.raw",
        description="Topic for raw audio chunks"
    )
    topic_device_sensor_raw: str = Field(
        default="device.sensor.{sensor_type}.raw",
        description="Topic pattern for sensor data"
    )
    topic_device_image_raw: str = Field(
        default="device.image.camera.raw",
        description="Topic for camera images"
    )
    
    # Monitoring
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=8001,
        description="Prometheus metrics port"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    
    model_config = {
        "env_prefix": "LOOM_",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings() 