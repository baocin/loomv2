"""Configuration for Kyutai-STT service."""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration."""

    # Service info
    service_name: str = "kyutai-stt"
    environment: str = "development"

    # API settings
    host: str = "0.0.0.0"
    port: int = 8002

    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "kyutai-stt-consumer"
    kafka_input_topic: str = "device.audio.raw"  # Process raw audio directly
    kafka_output_topic: str = "media.text.transcribed.words"
    kafka_max_poll_records: int = 10
    kafka_session_timeout_ms: int = 30000
    kafka_heartbeat_interval_ms: int = 10000

    # Model settings
    model_name: str = "kyutai/stt-1b-en_fr"  # Kyutai Moshi STT model
    model_device: str = "cuda" if os.path.exists("/usr/local/cuda") else "cpu"
    model_cache_dir: str | None = "/models"
    batch_size: int = 1
    # Kyutai STT specific settings
    use_sampling: bool = False  # Deterministic decoding as in Colab
    temp: float = 0.0  # Temperature for generation
    temp_text: float = 0.0  # Temperature for text generation

    # Audio settings
    target_sample_rate: int = 16000

    # Audio accumulation settings
    min_chunks_for_processing: int = 10  # Minimum chunks to accumulate before processing
    max_buffer_duration_ms: int = 30000  # Maximum buffer duration (30 seconds)
    buffer_timeout_seconds: float = 5.0  # Process buffer after this timeout

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Database settings
    database_url: str = "postgresql://loom:loom@postgres:5432/loom"
    database_pool_min_size: int = 2
    database_pool_max_size: int = 10

    class Config:
        env_prefix = "LOOM_"
        case_sensitive = False


settings = Settings()
