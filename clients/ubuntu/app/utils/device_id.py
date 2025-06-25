"""Device ID management for persistent UUID storage."""

import os
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class DeviceIDManager:
    """Manages persistent device UUID storage."""

    def __init__(self, config_dir: str | None = None):
        """Initialize device ID manager.

        Args:
            config_dir: Custom config directory, defaults to platform-specific location
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = self._get_default_config_dir()

        self.device_id_file = self.config_dir / "device_id"
        self._device_id: str | None = None

    def _get_default_config_dir(self) -> Path:
        """Get platform-specific default config directory."""
        platform = os.uname().sysname.lower()

        if platform == "darwin":  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / "pino-proxy"
        elif platform == "linux":  # Ubuntu/Linux
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "pino-proxy"
            else:
                config_dir = Path.home() / ".config" / "pino-proxy"
        else:  # Windows or other
            config_dir = Path.home() / ".pino-proxy"

        return config_dir

    def get_device_id(self) -> str:
        """Get or create persistent device ID."""
        if self._device_id:
            return self._device_id

        # Try to load existing device ID
        if self.device_id_file.exists():
            try:
                with open(self.device_id_file) as f:
                    device_id = f.read().strip()

                # Validate UUID format
                uuid.UUID(device_id)
                self._device_id = device_id
                logger.info("Loaded existing device ID", device_id=device_id)
                return device_id

            except (OSError, ValueError) as e:
                logger.warning(
                    "Invalid device ID file, generating new one", error=str(e)
                )

        # Generate new device ID
        device_id = str(uuid.uuid4())
        self._device_id = device_id

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save device ID
        try:
            with open(self.device_id_file, "w") as f:
                f.write(device_id)

            # Set appropriate permissions (user read/write only)
            os.chmod(self.device_id_file, 0o600)

            logger.info(
                "Generated new device ID",
                device_id=device_id,
                config_dir=str(self.config_dir),
            )

        except OSError as e:
            logger.error("Failed to save device ID", error=str(e))
            # Continue with in-memory device ID

        return device_id

    def reset_device_id(self) -> str:
        """Generate and save a new device ID."""
        # Remove existing file
        if self.device_id_file.exists():
            try:
                self.device_id_file.unlink()
                logger.info("Removed old device ID file")
            except OSError as e:
                logger.error("Failed to remove old device ID file", error=str(e))

        # Clear cached ID and generate new one
        self._device_id = None
        return self.get_device_id()

    @property
    def config_directory(self) -> Path:
        """Get the config directory path."""
        return self.config_dir

    def get_config_file_path(self, filename: str) -> Path:
        """Get path for a config file in the pino-proxy directory."""
        return self.config_dir / filename
