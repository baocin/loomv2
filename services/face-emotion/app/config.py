"""Configuration for face emotion detection service."""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with LOOM_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="LOOM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Service settings
    service_name: str = "face-emotion"
    host: str = "0.0.0.0"
    port: int = 8004
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "face-emotion-consumer"
    kafka_input_topic: str = "media.image.vision_annotations"
    kafka_output_topic: str = "analysis.image.face_emotions"
    kafka_auto_offset_reset: str = "earliest"
    kafka_enable_auto_commit: bool = False
    kafka_max_poll_records: int = 10
    kafka_consumer_timeout_ms: int = 1000

    # Model settings
    model_name: str = "trpakov/vit-face-expression"
    model_device: str = "cuda" if os.path.exists("/usr/local/cuda") else "cpu"
    model_cache_dir: Optional[str] = "/models"
    batch_size: int = 1

    # Face detection settings
    face_detection_confidence: float = 0.5
    min_face_size: int = 30  # Minimum face size in pixels
    max_faces_per_image: int = 10

    # Emotion settings
    emotion_classes: List[str] = [
        "anger",
        "contempt",
        "disgust",
        "fear",
        "happiness",
        "neutral",
        "sadness",
        "surprise",
    ]
    confidence_threshold: float = 0.1

    # Image processing settings
    max_image_size: int = 1024  # Resize images larger than this
    image_quality: int = 85

    # Performance settings
    processing_timeout_seconds: int = 30
    max_concurrent_processes: int = 2

    # Health check settings
    health_check_interval_seconds: int = 30


settings = Settings()
