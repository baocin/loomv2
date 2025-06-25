"""Configuration settings for pino-proxy Ubuntu client."""

import os


class Config:
    """Configuration class for pino-proxy Ubuntu."""

    def __init__(self):
        """Initialize configuration from environment variables with defaults."""

        # API Configuration
        self.api_base_url = os.getenv("LOOM_API_URL", "http://localhost:8000")
        self.api_timeout = float(os.getenv("LOOM_API_TIMEOUT", "30.0"))

        # System collector configuration
        self.system_poll_interval = float(os.getenv("SYSTEM_POLL_INTERVAL", "5.0"))
        self.system_send_interval = float(os.getenv("SYSTEM_SEND_INTERVAL", "30.0"))

        # Audio collector configuration
        self.audio_poll_interval = float(os.getenv("AUDIO_POLL_INTERVAL", "2.0"))
        self.audio_send_interval = float(os.getenv("AUDIO_SEND_INTERVAL", "10.0"))
        self.audio_sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE", "44100"))
        self.audio_channels = int(os.getenv("AUDIO_CHANNELS", "1"))
        self.audio_format = os.getenv("AUDIO_FORMAT", "wav")

        # Screen capture configuration
        self.screen_poll_interval = float(os.getenv("SCREEN_POLL_INTERVAL", "30.0"))
        self.screen_send_interval = float(os.getenv("SCREEN_SEND_INTERVAL", "60.0"))
        self.screen_quality = int(os.getenv("SCREEN_QUALITY", "80"))
        self.screen_max_width = int(os.getenv("SCREEN_MAX_WIDTH", "1920"))
        self.screen_max_height = int(os.getenv("SCREEN_MAX_HEIGHT", "1080"))

        # Apps monitoring configuration
        self.apps_poll_interval = float(os.getenv("APPS_POLL_INTERVAL", "10.0"))
        self.apps_send_interval = float(os.getenv("APPS_SEND_INTERVAL", "60.0"))

        # Location configuration
        self.location_poll_interval = float(os.getenv("LOCATION_POLL_INTERVAL", "60.0"))
        self.location_send_interval = float(
            os.getenv("LOCATION_SEND_INTERVAL", "300.0")
        )

        # Clipboard configuration
        self.clipboard_poll_interval = float(
            os.getenv("CLIPBOARD_POLL_INTERVAL", "1.0")
        )
        self.clipboard_send_interval = float(
            os.getenv("CLIPBOARD_SEND_INTERVAL", "5.0")
        )
        self.clipboard_max_length = int(os.getenv("CLIPBOARD_MAX_LENGTH", "10000"))

        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "json")

        # Device configuration
        self.device_name = os.getenv("DEVICE_NAME") or self._get_hostname()
        self.device_type = "ubuntu_client"

        # Validation
        self._validate_config()

    def _get_hostname(self) -> str:
        """Get system hostname."""
        import socket

        try:
            return socket.gethostname()
        except Exception:
            return "ubuntu-unknown"

    def _validate_config(self) -> None:
        """Validate configuration values."""
        # Validate intervals
        if self.system_send_interval < self.system_poll_interval:
            raise ValueError("System send interval must be >= poll interval")

        if self.audio_send_interval < self.audio_poll_interval:
            raise ValueError("Audio send interval must be >= poll interval")

        if self.screen_send_interval < self.screen_poll_interval:
            raise ValueError("Screen send interval must be >= poll interval")

        if self.apps_send_interval < self.apps_poll_interval:
            raise ValueError("Apps send interval must be >= poll interval")

        if self.location_send_interval < self.location_poll_interval:
            raise ValueError("Location send interval must be >= poll interval")

        if self.clipboard_send_interval < self.clipboard_poll_interval:
            raise ValueError("Clipboard send interval must be >= poll interval")

        # Validate positive values
        positive_values = [
            self.system_poll_interval,
            self.system_send_interval,
            self.audio_poll_interval,
            self.audio_send_interval,
            self.screen_poll_interval,
            self.screen_send_interval,
            self.apps_poll_interval,
            self.apps_send_interval,
            self.location_poll_interval,
            self.location_send_interval,
            self.clipboard_poll_interval,
            self.clipboard_send_interval,
            self.api_timeout,
        ]

        for value in positive_values:
            if value <= 0:
                raise ValueError(
                    f"All intervals and timeout must be positive, got: {value}"
                )

        # Validate ranges
        if not (1 <= self.screen_quality <= 100):
            raise ValueError("Screen quality must be between 1 and 100")

        if self.screen_max_width < 100 or self.screen_max_height < 100:
            raise ValueError("Screen dimensions must be at least 100x100")

        if self.audio_sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            raise ValueError("Audio sample rate must be a standard value")

        if self.audio_channels not in [1, 2]:
            raise ValueError("Audio channels must be 1 (mono) or 2 (stereo)")

    def get_collector_config(self, collector_name: str) -> dict:
        """Get configuration for a specific collector."""
        configs = {
            "system": {
                "poll_interval": self.system_poll_interval,
                "send_interval": self.system_send_interval,
            },
            "audio": {
                "poll_interval": self.audio_poll_interval,
                "send_interval": self.audio_send_interval,
                "sample_rate": self.audio_sample_rate,
                "channels": self.audio_channels,
                "format": self.audio_format,
            },
            "screen": {
                "poll_interval": self.screen_poll_interval,
                "send_interval": self.screen_send_interval,
                "quality": self.screen_quality,
                "max_width": self.screen_max_width,
                "max_height": self.screen_max_height,
            },
            "apps": {
                "poll_interval": self.apps_poll_interval,
                "send_interval": self.apps_send_interval,
            },
            "location": {
                "poll_interval": self.location_poll_interval,
                "send_interval": self.location_send_interval,
            },
            "clipboard": {
                "poll_interval": self.clipboard_poll_interval,
                "send_interval": self.clipboard_send_interval,
                "max_length": self.clipboard_max_length,
            },
        }

        return configs.get(collector_name, {})

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "api_base_url": self.api_base_url,
            "api_timeout": self.api_timeout,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "collectors": {
                "system": self.get_collector_config("system"),
                "audio": self.get_collector_config("audio"),
                "screen": self.get_collector_config("screen"),
                "apps": self.get_collector_config("apps"),
                "location": self.get_collector_config("location"),
                "clipboard": self.get_collector_config("clipboard"),
            },
        }
