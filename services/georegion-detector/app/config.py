"""Configuration for Georegion Detection Consumer"""
from pydantic_settings import BaseSettings
from typing import List, Dict, Any


class Settings(BaseSettings):
    # Kafka Configuration
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group_id: str = "georegion-detector"
    kafka_input_topic: str = "location.address.geocoded"
    kafka_output_topic: str = "location.georegion.detected"
    
    # Database Configuration
    database_url: str = "postgresql://loom:loom@localhost:5432/loom"
    
    # Georegion Detection Configuration
    detection_radius_meters: float = 100.0  # Default radius for georegion detection
    
    # Service Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Default georegions (can be overridden by database)
    default_georegions: List[Dict[str, Any]] = [
        {
            "id": "home",
            "name": "Home",
            "type": "residence",
            "latitude": 37.7749,  # Example: San Francisco
            "longitude": -122.4194,
            "radius_meters": 50.0
        },
        {
            "id": "work",
            "name": "Work",
            "type": "workplace",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "radius_meters": 100.0
        }
    ]
    
    class Config:
        env_prefix = "LOOM_"
        case_sensitive = False


settings = Settings()