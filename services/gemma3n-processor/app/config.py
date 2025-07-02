"""Configuration for Gemma 3N Processor service."""

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
    service_name: str = "gemma3n-processor"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # Kafka configuration
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_input_topics: List[str] = [
        "media.text.transcribed.words",
        "device.image.camera.raw",
        "device.video.screen.raw",
        "media.audio.vad_filtered",
    ]
    kafka_output_topic: str = "analysis.multimodal.gemma3n_results"
    kafka_consumer_group: str = "gemma3n-processor-consumer"
    kafka_auto_offset_reset: str = "earliest"
    kafka_compression_type: str = "lz4"

    # Ollama configuration
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3n:e4b"  # Using 4B parameter model
    ollama_timeout: int = 60
    ollama_keep_alive: int = 300  # Keep model loaded for 5 minutes

    # Model configuration
    model_device: Optional[str] = None  # None for auto-detect, 'cuda' or 'cpu'
    model_max_tokens: int = 4096  # Gemma 3N supports up to 32K tokens
    model_temperature: float = 0.7
    model_top_p: float = 0.9

    # Processing configuration
    max_image_size: int = 768  # Gemma 3N supports up to 768x768
    max_audio_duration: int = 30  # Max audio duration in seconds
    batch_size: int = 1  # Process one at a time for multimodal
    processing_timeout: int = 120  # Increased timeout for multimodal processing

    # Health check configuration
    health_check_interval: int = 30
    readiness_timeout: int = 10


# Global settings instance
settings = Settings()
