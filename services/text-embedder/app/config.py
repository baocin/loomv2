"""Configuration for text embedder service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_prefix="LOOM_")

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "text-embedder-consumer"
    kafka_email_topic: str = "external.email.events.raw"
    kafka_twitter_topic: str = "external.twitter.liked.raw"
    kafka_embedded_email_topic: str = "analysis.text.embedded.emails"
    kafka_embedded_twitter_topic: str = "analysis.text.embedded.twitter"

    # Database settings
    database_url: str = "postgresql://loom:loom@localhost:5432/loom"

    # Model settings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"
    batch_size: int = 32

    # Service settings
    host: str = "0.0.0.0"
    port: int = 8006
    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()