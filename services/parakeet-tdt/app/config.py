"""Configuration for Parakeet-TDT service."""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration."""
    
    # Service info
    service_name: str = "parakeet-tdt"
    environment: str = "development"
    
    # API settings
    host: str = "0.0.0.0"
    port: int = 8002
    
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group: str = "parakeet-tdt-consumer"
    kafka_input_topic: str = "media.audio.vad_filtered"
    kafka_output_topic: str = "media.text.word_timestamps"
    kafka_max_poll_records: int = 10
    kafka_session_timeout_ms: int = 30000
    kafka_heartbeat_interval_ms: int = 10000
    
    # Model settings
    model_name: str = "nvidia/parakeet-tdt_ctc-1.1b"
    model_device: str = "cuda" if os.path.exists("/usr/local/cuda") else "cpu"
    model_cache_dir: Optional[str] = "/models"
    batch_size: int = 1
    
    # Audio settings
    target_sample_rate: int = 16000
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_prefix = "LOOM_"
        case_sensitive = False


settings = Settings()