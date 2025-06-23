"""Configuration settings for scheduled consumers."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Kafka configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka bootstrap servers"
    )
    kafka_client_id: str = Field(
        default="loom-scheduled-consumers",
        description="Kafka client ID"
    )
    kafka_default_partitions: int = Field(
        default=3,
        description="Default number of partitions for new topics"
    )
    kafka_default_replication_factor: int = Field(
        default=1,
        description="Default replication factor for new topics"
    )
    
    # Scheduling configuration
    scheduler_interval_seconds: int = Field(
        default=300,  # 5 minutes
        description="Base scheduler check interval in seconds"
    )
    max_concurrent_jobs: int = Field(
        default=5,
        description="Maximum concurrent scheduled jobs"
    )
    
    # External API configurations
    email_check_interval_minutes: int = Field(
        default=15,
        description="Email check interval in minutes"
    )
    calendar_sync_interval_minutes: int = Field(
        default=30,
        description="Calendar sync interval in minutes"
    )
    social_media_check_interval_minutes: int = Field(
        default=60,
        description="Social media check interval in minutes"
    )
    web_activity_check_interval_minutes: int = Field(
        default=10,
        description="Web activity check interval in minutes"
    )
    
    # API credentials (should be set via environment variables)
    twitter_bearer_token: str = Field(default="", description="Twitter/X API bearer token")
    gmail_credentials_path: str = Field(default="", description="Gmail API credentials file path")
    calendar_credentials_path: str = Field(default="", description="Calendar API credentials file path")
    
    # Browser data paths
    chrome_history_path: str = Field(
        default="",
        description="Path to Chrome browser history database"
    )
    firefox_history_path: str = Field(
        default="",
        description="Path to Firefox browser history database"
    )
    
    # Hacker News configuration
    hackernews_user_id: str = Field(
        default="",
        description="Hacker News user ID for fetching liked/upvoted items"
    )
    
    # Reddit configuration
    reddit_username: str = Field(default="", description="Reddit username")
    reddit_client_id: str = Field(default="", description="Reddit API client ID")
    reddit_client_secret: str = Field(default="", description="Reddit API client secret")
    
    # RSS feeds
    rss_feeds: List[str] = Field(
        default_factory=lambda: [
            "https://feeds.feedburner.com/oreilly/radar",
            "https://blog.cloudflare.com/rss/",
            "https://aws.amazon.com/blogs/aws/feed/",
        ],
        description="List of RSS feed URLs to monitor"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Device identification
    device_id: str = Field(
        default="scheduled-consumer-service",
        description="Device ID for data attribution"
    )
    
    model_config = {
        "env_prefix": "LOOM_",
        "env_file": ".env",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()