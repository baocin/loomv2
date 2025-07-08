"""Configuration settings for ONNX-VAD service."""

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation."""

    # Service Configuration
    service_name: str = "onnx-vad"
    environment: str = Field(default="development", alias="LOOM_ENVIRONMENT")
    host: str = Field(default="0.0.0.0", alias="LOOM_HOST")  # nosec
    port: int = Field(default=8001, alias="LOOM_PORT")
    log_level: str = Field(default="INFO", alias="LOOM_LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOOM_LOG_FORMAT")

    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="LOOM_KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_consumer_group: str = Field(
        default="onnx-vad-consumer-group", alias="LOOM_KAFKA_CONSUMER_GROUP_ID"
    )
    kafka_input_topic: str = Field(
        default="device.audio.raw", alias="LOOM_KAFKA_INPUT_TOPIC"
    )
    kafka_output_topic: str = Field(
        default="media.audio.vad_filtered", alias="LOOM_KAFKA_OUTPUT_TOPIC"
    )
    kafka_max_batch_size: int = Field(default=10, alias="LOOM_KAFKA_MAX_BATCH_SIZE")
    kafka_max_wait_time: float = Field(default=5.0, alias="LOOM_KAFKA_MAX_WAIT_TIME")

    # Model Configuration
    model_name: str = Field(default="snakers4/silero-vad", alias="VAD_MODEL_NAME")
    model_device: str = Field(
        default="cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu",
        alias="VAD_MODEL_DEVICE",
    )

    # VAD Settings
    vad_threshold: float = Field(default=0.5, alias="VAD_THRESHOLD")
    vad_min_speech_duration_ms: int = Field(
        default=250, alias="VAD_MIN_SPEECH_DURATION_MS"
    )
    vad_min_silence_duration_ms: int = Field(
        default=100, alias="VAD_MIN_SILENCE_DURATION_MS"
    )
    vad_window_size_samples: int = Field(default=512, alias="VAD_WINDOW_SIZE_SAMPLES")
    vad_sample_rate: int = Field(default=16000, alias="VAD_SAMPLE_RATE")

    # Performance
    enable_batching: bool = Field(default=True, alias="VAD_ENABLE_BATCHING")
    batch_timeout_seconds: float = Field(default=2.0, alias="VAD_BATCH_TIMEOUT")
    max_batch_size: int = Field(default=8, alias="VAD_MAX_BATCH_SIZE")

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
