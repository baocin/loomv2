"""Configuration for significant motion detection service."""

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
    service_name: str = "significant-motion-detector"
    host: str = "0.0.0.0"
    port: int = 8013
    log_level: str = "INFO"
    environment: str = "development"
    
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group_id: str = "significant-motion-detector"
    kafka_input_topic: str = "device.sensor.accelerometer.raw"
    kafka_output_topic: str = "motion.events.significant"
    kafka_auto_offset_reset: str = "earliest"
    
    # Motion detection settings
    motion_window_seconds: float = 2.0  # Window size for motion analysis
    motion_threshold_ms2: float = 2.0  # Minimum acceleration magnitude change (m/s²)
    motion_min_duration_seconds: float = 0.5  # Minimum duration of motion
    motion_cooldown_seconds: float = 5.0  # Cooldown between events
    
    # Activity detection thresholds (m/s²)
    activity_walking_threshold: float = 2.0
    activity_running_threshold: float = 5.0
    activity_vehicle_threshold: float = 1.0
    activity_stationary_threshold: float = 0.5
    
    # Database settings (for deduplication)
    database_url: str = "postgresql://loom:loom@postgres:5432/loom"


settings = Settings()