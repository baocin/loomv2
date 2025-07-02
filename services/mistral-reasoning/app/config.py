"""Configuration for Mistral reasoning service."""

from typing import List

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
    service_name: str = "mistral-reasoning"
    host: str = "0.0.0.0"
    port: int = 8005
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "mistral-reasoning-consumer"
    kafka_input_topics: List[str] = [
        "media.text.word_timestamps",
        "task.url.processed_content",
        "analysis.audio.emotion_scores",
        "analysis.image.face_emotions",
    ]
    kafka_output_topic: str = "analysis.context.reasoning_chains"
    kafka_auto_offset_reset: str = "earliest"
    kafka_enable_auto_commit: bool = False
    kafka_max_poll_records: int = 10
    kafka_consumer_timeout_ms: int = 5000  # Longer timeout for reasoning

    # Ollama settings
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "mistral:7b"
    ollama_timeout: int = 120  # 2 minutes for complex reasoning
    ollama_num_ctx: int = 8192  # Context window size
    ollama_temperature: float = 0.3  # Lower temperature for more consistent reasoning

    # Reasoning settings
    reasoning_window_minutes: int = 10  # Window for collecting related data
    max_input_tokens: int = 6000  # Maximum tokens for input context
    min_confidence_threshold: float = 0.3

    # Context types
    context_types: List[str] = [
        "conversation",
        "activity",
        "location",
        "emotion",
        "focus",
        "productivity",
    ]

    # Processing settings
    batch_timeout_seconds: int = 30
    max_concurrent_processes: int = 1  # Sequential processing for reasoning
    processing_timeout_seconds: int = 180  # 3 minutes max per reasoning task

    # Health check settings
    health_check_interval_seconds: int = 30


settings = Settings()
