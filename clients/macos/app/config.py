"""Configuration management for the macOS client."""

import os
from typing import Any

from pydantic import BaseSettings, Field


class LoomConfig(BaseSettings):
    """Configuration for the Loom macOS client."""

    # API Configuration
    api_base_url: str = Field(
        default="http://localhost:8000",
        env="LOOM_API_BASE_URL",
        description="Base URL for the Loom ingestion API",
    )

    device_id: str = Field(
        default_factory=lambda: f"macos-{os.uname().nodename}",
        env="LOOM_DEVICE_ID",
        description="Unique device identifier",
    )

    # Logging
    log_level: str = Field(
        default="INFO", env="LOOM_LOG_LEVEL", description="Logging level"
    )

    # Data Collection Toggles
    audio_enabled: bool = Field(
        default=True, env="LOOM_AUDIO_ENABLED", description="Enable audio recording"
    )

    screen_enabled: bool = Field(
        default=True, env="LOOM_SCREEN_ENABLED", description="Enable screen capture"
    )

    system_enabled: bool = Field(
        default=True, env="LOOM_SYSTEM_ENABLED", description="Enable system monitoring"
    )

    location_enabled: bool = Field(
        default=False,
        env="LOOM_LOCATION_ENABLED",
        description="Enable location services",
    )

    clipboard_enabled: bool = Field(
        default=True,
        env="LOOM_CLIPBOARD_ENABLED",
        description="Enable clipboard monitoring",
    )

    apps_enabled: bool = Field(
        default=True,
        env="LOOM_APPS_ENABLED",
        description="Enable application monitoring",
    )

    # Collection Intervals (seconds)
    audio_interval: int = Field(
        default=10,
        env="LOOM_AUDIO_INTERVAL",
        description="Audio chunk duration in seconds",
    )

    screen_interval: int = Field(
        default=30,
        env="LOOM_SCREEN_INTERVAL",
        description="Screenshot interval in seconds",
    )

    system_interval: int = Field(
        default=60,
        env="LOOM_SYSTEM_INTERVAL",
        description="System metrics interval in seconds",
    )

    location_interval: int = Field(
        default=300,
        env="LOOM_LOCATION_INTERVAL",
        description="GPS check interval in seconds",
    )

    clipboard_interval: int = Field(
        default=5,
        env="LOOM_CLIPBOARD_INTERVAL",
        description="Clipboard check interval in seconds",
    )

    apps_interval: int = Field(
        default=10,
        env="LOOM_APPS_INTERVAL",
        description="Application monitoring interval in seconds",
    )

    # Audio Settings
    audio_sample_rate: int = Field(
        default=44100, env="LOOM_AUDIO_SAMPLE_RATE", description="Audio sample rate"
    )

    audio_channels: int = Field(
        default=1,
        env="LOOM_AUDIO_CHANNELS",
        description="Audio channels (1=mono, 2=stereo)",
    )

    audio_format: str = Field(
        default="wav",
        env="LOOM_AUDIO_FORMAT",
        description="Audio format (wav, mp3, aac)",
    )

    # Screen Settings
    screen_quality: int = Field(
        default=80, env="LOOM_SCREEN_QUALITY", description="Screenshot quality (0-100)"
    )

    screen_max_width: int = Field(
        default=1920,
        env="LOOM_SCREEN_MAX_WIDTH",
        description="Maximum screenshot width",
    )

    screen_max_height: int = Field(
        default=1080,
        env="LOOM_SCREEN_MAX_HEIGHT",
        description="Maximum screenshot height",
    )

    # Local API Server
    server_host: str = Field(
        default="127.0.0.1", env="LOOM_SERVER_HOST", description="Local API server host"
    )

    server_port: int = Field(
        default=8080, env="LOOM_SERVER_PORT", description="Local API server port"
    )

    # Storage
    data_dir: str = Field(
        default="./data",
        env="LOOM_DATA_DIR",
        description="Local data storage directory",
    )

    log_dir: str = Field(
        default="./logs", env="LOOM_LOG_DIR", description="Log storage directory"
    )

    # Privacy Settings
    exclude_secure_input: bool = Field(
        default=True,
        env="LOOM_EXCLUDE_SECURE_INPUT",
        description="Exclude secure input fields from capture",
    )

    exclude_private_browsing: bool = Field(
        default=True,
        env="LOOM_EXCLUDE_PRIVATE_BROWSING",
        description="Exclude private browsing from monitoring",
    )

    exclude_passwords: bool = Field(
        default=True,
        env="LOOM_EXCLUDE_PASSWORDS",
        description="Exclude password fields from capture",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.dict()

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @property
    def enabled_collectors(self) -> dict[str, bool]:
        """Get enabled collectors mapping."""
        return {
            "audio": self.audio_enabled,
            "screen": self.screen_enabled,
            "system": self.system_enabled,
            "location": self.location_enabled,
            "clipboard": self.clipboard_enabled,
            "apps": self.apps_enabled,
        }

    @property
    def collection_intervals(self) -> dict[str, int]:
        """Get collection intervals mapping."""
        return {
            "audio": self.audio_interval,
            "screen": self.screen_interval,
            "system": self.system_interval,
            "location": self.location_interval,
            "clipboard": self.clipboard_interval,
            "apps": self.apps_interval,
        }


# Global configuration instance
config = LoomConfig()
