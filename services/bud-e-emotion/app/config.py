"""Configuration for BUD-E emotion analysis service."""

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
    service_name: str = "bud-e-emotion"
    host: str = "0.0.0.0"
    port: int = 8003
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "bud-e-emotion-consumer"
    kafka_input_topic: str = "media.audio.vad_filtered"
    kafka_output_topic: str = "analysis.audio.emotion_scores"
    kafka_auto_offset_reset: str = "latest"
    kafka_enable_auto_commit: bool = False
    kafka_max_poll_records: int = 10
    kafka_consumer_timeout_ms: int = 1000

    # Model settings
    model_name: str = "laion/BUD-E_Whisper"
    model_device: str = "cuda" if os.path.exists("/usr/local/cuda") else "cpu"
    model_cache_dir: Optional[str] = "/models"
    batch_size: int = 1

    # Audio processing settings
    target_sample_rate: int = 16000
    max_audio_length_seconds: int = 30

    # Emotion settings
    emotion_classes: List[str] = [
        "anger", "disgust", "fear", "happiness", 
        "sadness", "surprise", "neutral"
    ]
    confidence_threshold: float = 0.1

    # Performance settings
    processing_timeout_seconds: int = 30
    max_concurrent_processes: int = 2

    # Health check settings
    health_check_interval_seconds: int = 30


settings = Settings()