"""Configuration for Silero VAD service."""

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
    service_name: str = "silero-vad"
    host: str = "0.0.0.0"  # nosec B104 - binding to all interfaces in container
    port: int = 8001
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "silero-vad-consumer"
    kafka_input_topic: str = "device.audio.raw"
    kafka_output_topic: str = "media.audio.vad_filtered"
    kafka_auto_offset_reset: str = "earliest"
    kafka_enable_auto_commit: bool = False
    kafka_max_poll_records: int = 10
    kafka_consumer_timeout_ms: int = 5000  # 5 seconds for better polling
    kafka_session_timeout_ms: int = 30000  # 30 seconds
    kafka_heartbeat_interval_ms: int = 3000  # 3 seconds
    kafka_max_poll_interval_ms: int = 300000  # 5 minutes for slow processing

    # VAD settings
    vad_threshold: float = 0.3  # Lowered from 0.5 for more sensitivity
    vad_min_speech_duration_ms: float = (
        100.0  # Reduced from 250ms to catch shorter utterances
    )
    vad_min_silence_duration_ms: float = (
        300.0  # Increased from 100ms to avoid cutting off speech
    )
    vad_window_size_samples: int = 512  # 16ms at 16kHz
    vad_sample_rate: int = 16000  # Silero VAD expects 16kHz

    # Model settings
    silero_model_name: str = "silero_vad"
    silero_model_version: str = "v4.0"
    silero_use_onnx: bool = True  # Use ONNX for better stability
    silero_model_cache_path: str = (
        "/data/models/silero-vad"  # Path to store models persistently
    )

    # Performance settings
    batch_timeout_ms: int = 100
    max_batch_size: int = 1  # Process one at a time for now

    # Health check settings
    health_check_interval_seconds: int = 30
    kafka_health_timeout_seconds: int = 5

    # Database settings
    database_url: str = "postgresql://loom:loom@postgres:5432/loom"
    database_pool_min_size: int = 2
    database_pool_max_size: int = 10


settings = Settings()
