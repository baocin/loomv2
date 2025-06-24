"""Configuration for Nomic Embed Vision service."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Service configuration
    service_name: str = "nomic-embed"
    host: str = Field(default="0.0.0.0", alias="NOMIC_EMBED_HOST")
    port: int = Field(default=8004, alias="NOMIC_EMBED_PORT")
    log_level: str = Field(default="INFO", alias="NOMIC_EMBED_LOG_LEVEL")
    environment: str = Field(default="development", alias="NOMIC_EMBED_ENVIRONMENT")

    # Model configuration
    model_name: str = Field(
        default="nomic-ai/nomic-embed-vision-v1.5", alias="NOMIC_EMBED_MODEL_NAME"
    )
    device: str = Field(default="auto", alias="NOMIC_EMBED_DEVICE")  # auto, cpu, cuda
    max_batch_size: int = Field(default=32, alias="NOMIC_EMBED_MAX_BATCH_SIZE")
    model_cache_dir: str = Field(
        default="./models", alias="NOMIC_EMBED_MODEL_CACHE_DIR"
    )
    trust_remote_code: bool = Field(default=True, alias="NOMIC_EMBED_TRUST_REMOTE_CODE")

    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    kafka_group_id: str = Field(
        default="nomic-embed-group", alias="NOMIC_EMBED_KAFKA_GROUP_ID"
    )
    kafka_auto_offset_reset: str = Field(
        default="latest", alias="NOMIC_EMBED_KAFKA_AUTO_OFFSET_RESET"
    )
    kafka_enable_auto_commit: bool = Field(
        default=True, alias="NOMIC_EMBED_KAFKA_ENABLE_AUTO_COMMIT"
    )

    # Input topics (text and image data to embed)
    text_input_topics: list[str] = Field(
        default=[
            "device.text.notes.raw",
            "media.text.transcribed.words",
            "task.url.processed.content",
            "task.github.processed.content",
            "task.document.processed.content",
        ],
        alias="NOMIC_EMBED_TEXT_INPUT_TOPICS",
    )

    image_input_topics: list[str] = Field(
        default=[
            "device.image.camera.raw",
            "device.video.screen.raw",
        ],
        alias="NOMIC_EMBED_IMAGE_INPUT_TOPICS",
    )

    # Output topics (embedded data)
    text_embedding_topic: str = Field(
        default="embeddings.text.nomic", alias="NOMIC_EMBED_TEXT_OUTPUT_TOPIC"
    )
    image_embedding_topic: str = Field(
        default="embeddings.image.nomic", alias="NOMIC_EMBED_IMAGE_OUTPUT_TOPIC"
    )

    # Database configuration
    database_url: str = Field(
        default="postgresql://loom:loom@localhost:5432/loom", alias="DATABASE_URL"
    )

    # Processing configuration
    max_text_length: int = Field(default=8192, alias="NOMIC_EMBED_MAX_TEXT_LENGTH")
    max_image_size: int = Field(
        default=2048,
        alias="NOMIC_EMBED_MAX_IMAGE_SIZE",  # pixels
    )
    embedding_dimension: int = Field(
        default=768,
        alias="NOMIC_EMBED_DIMENSION",  # Nomic embed dimension
    )

    # Performance settings
    worker_concurrency: int = Field(default=4, alias="NOMIC_EMBED_WORKER_CONCURRENCY")
    max_queue_size: int = Field(default=1000, alias="NOMIC_EMBED_MAX_QUEUE_SIZE")
    batch_timeout_seconds: float = Field(default=1.0, alias="NOMIC_EMBED_BATCH_TIMEOUT")

    # Health check configuration
    health_check_timeout: float = Field(
        default=30.0, alias="NOMIC_EMBED_HEALTH_CHECK_TIMEOUT"
    )

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
