"""Configuration settings for ONNX-ASR service."""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""

    # Service Configuration
    service_name: str = "onnx-asr"
    environment: str = Field(default="development", alias="LOOM_ENVIRONMENT")
    host: str = Field(default="0.0.0.0", alias="LOOM_HOST")  # nosec
    port: int = Field(default=8002, alias="LOOM_PORT")
    log_level: str = Field(default="INFO", alias="LOOM_LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOOM_LOG_FORMAT")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="LOOM_KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_consumer_group: str = Field(
        default="onnx-asr-consumer-group", alias="LOOM_KAFKA_CONSUMER_GROUP_ID"
    )
    kafka_input_topic: str = Field(
        default="device.audio.raw", alias="LOOM_KAFKA_INPUT_TOPIC"
    )
    kafka_output_topic: str = Field(
        default="media.text.transcribed.words", alias="LOOM_KAFKA_OUTPUT_TOPIC"
    )
    kafka_max_batch_size: int = Field(default=10, alias="LOOM_KAFKA_MAX_BATCH_SIZE")
    kafka_max_wait_time: float = Field(default=5.0, alias="LOOM_KAFKA_MAX_WAIT_TIME")
    kafka_max_retries: int = Field(default=3, alias="LOOM_KAFKA_MAX_RETRIES")
    kafka_retry_backoff_ms: int = Field(
        default=1000, alias="LOOM_KAFKA_RETRY_BACKOFF_MS"
    )

    # Model Configuration
    model_name: str = Field(default="nvidia/parakeet-tdt-0.6b", alias="ASR_MODEL_NAME")
    model_device: str = Field(
        default="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu",
        alias="ASR_MODEL_DEVICE",
    )
    batch_size: int = Field(default=8, alias="ASR_BATCH_SIZE")
    num_workers: int = Field(default=2, alias="ASR_NUM_WORKERS")

    # Audio Processing
    target_sample_rate: int = Field(default=16000, alias="ASR_TARGET_SAMPLE_RATE")
    max_audio_length_seconds: int = Field(default=30, alias="ASR_MAX_AUDIO_LENGTH")

    # Performance
    enable_batching: bool = Field(default=True, alias="ASR_ENABLE_BATCHING")
    batch_timeout_seconds: float = Field(default=2.0, alias="ASR_BATCH_TIMEOUT")
    max_batch_size: int = Field(default=8, alias="ASR_MAX_BATCH_SIZE")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
