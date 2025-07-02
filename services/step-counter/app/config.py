"""Configuration for step counter service."""

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
    service_name: str = "step-counter"
    host: str = "0.0.0.0"
    port: int = 8014
    log_level: str = "INFO"
    environment: str = "development"
    
    # Kafka settings
    kafka_bootstrap_servers: str = "kafka:29092"
    kafka_consumer_group_id: str = "step-counter"
    kafka_input_topic: str = "device.sensor.accelerometer.raw"
    kafka_output_topic: str = "device.health.steps.raw"
    kafka_auto_offset_reset: str = "earliest"
    
    # Step detection settings
    step_window_seconds: float = 5.0  # Window size for step analysis
    step_threshold_ms2: float = 1.5  # Minimum acceleration for step detection
    step_frequency_min_hz: float = 0.5  # Minimum step frequency (0.5 Hz = 30 steps/min)
    step_frequency_max_hz: float = 3.0  # Maximum step frequency (3 Hz = 180 steps/min)
    
    # Calibration settings
    stride_length_meters: float = 0.7  # Default stride length
    calories_per_meter: float = 0.05  # Calories burned per meter walked


settings = Settings()