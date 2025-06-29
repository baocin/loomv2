"""Configuration for Moondream Station service."""

from typing import List

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
    service_name: str = "moondream-station"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # Kafka configuration
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_input_topics: List[str] = [
        "device.image.camera.raw",
        "device.video.screen.raw",
        "task.image.analyze",
    ]
    kafka_output_topic: str = "media.image.analysis.moondream_results"
    kafka_consumer_group: str = "moondream-station-consumer"
    kafka_auto_offset_reset: str = "latest"
    kafka_compression_type: str = "lz4"

    # Moondream Station configuration
    moondream_host: str = "http://localhost:2020"
    moondream_api_path: str = "/v1"
    moondream_timeout: int = 30
    moondream_max_retries: int = 3

    # Processing configuration
    max_image_size: int = 2048  # Max dimension for image resizing
    jpeg_quality: int = 95  # JPEG compression quality
    batch_size: int = 1  # Process one image at a time
    processing_timeout: int = 60  # Timeout per image

    # Model configuration
    default_caption_prompt: str = "Describe this image in detail."
    enable_object_detection: bool = True
    enable_ocr: bool = True
    confidence_threshold: float = 0.7

    # Health check configuration
    health_check_interval: int = 30
    readiness_timeout: int = 5

    # Storage configuration
    temp_storage_path: str = "/app/data/temp"
    max_temp_storage_mb: int = 1000


# Global settings instance
settings = Settings()
