"""Configuration for MiniCPM-Vision service."""

from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="LOOM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service configuration
    service_name: str = "minicpm-vision"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # Kafka configuration
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_input_topics: List[str] = [
        "device.image.camera.raw",
        "device.video.screen.raw",
    ]
    kafka_output_topic: str = "media.image.vision_annotations"
    kafka_consumer_group: str = "minicpm-vision-consumer"
    kafka_auto_offset_reset: str = "earliest"
    kafka_compression_type: str = "lz4"

    # Model configuration
    model_device: Optional[str] = None  # None for auto-detect, 'cuda' or 'cpu'
    model_name: str = "openbmb/MiniCPM-Llama3-V-2_5"
    model_cache_dir: Optional[str] = None
    model_max_tokens: int = 1024
    model_temperature: float = 0.7

    # Processing configuration
    max_image_size: int = 1920  # Max dimension for image resizing
    batch_size: int = 1  # Number of images to process in parallel
    processing_timeout: int = 60  # Timeout in seconds per image

    # Health check configuration
    health_check_interval: int = 30
    readiness_timeout: int = 5

    # Database settings
    database_url: str = "postgresql://loom:loom@postgres:5432/loom"
    database_pool_min_size: int = 2
    database_pool_max_size: int = 10


# Global settings instance
settings = Settings()
