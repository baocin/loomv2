"""Configuration for activity classification service."""

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
    service_name: str = "activity-classifier"
    host: str = "0.0.0.0"
    port: int = 8015
    log_level: str = "INFO"
    environment: str = "development"
    
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group_id: str = "activity-classifier"
    kafka_input_topics: str = "motion.events.significant,device.sensor.gps.raw,device.health.steps.raw"
    kafka_output_topic: str = "motion.classification.activity"
    kafka_auto_offset_reset: str = "earliest"
    
    # Classification settings
    classification_window_seconds: float = 60.0  # Window for activity classification
    location_radius_meters: float = 100.0  # Radius for location-based classification
    
    # Activity thresholds
    activity_min_steps_per_minute: int = 30  # Minimum steps to consider walking
    activity_running_steps_per_minute: int = 120  # Threshold for running
    activity_vehicle_speed_ms: float = 5.0  # Speed threshold for vehicle detection
    activity_stationary_speed_ms: float = 0.5  # Speed threshold for stationary


settings = Settings()