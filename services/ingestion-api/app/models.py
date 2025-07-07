"""Pydantic models for ingestion API data structures."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class BaseMessage(BaseModel):
    """Base message structure for all Kafka messages."""

    schema_version: str = Field(default="1.0", description="Message schema version")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Message timestamp",
    )
    device_id: str = Field(description="Device identifier")
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message ID",
    )


class AudioChunk(BaseMessage):
    """Audio chunk data from microphone."""

    chunk_data: bytes = Field(description="Raw audio chunk data")
    sample_rate: int = Field(description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    format: str = Field(default="wav", description="Audio format")
    duration_ms: int = Field(description="Chunk duration in milliseconds")
    file_id: str | None = Field(
        default=None,
        description="Associated file ID for chunking",
    )


class SensorReading(BaseMessage):
    """Generic sensor reading."""

    sensor_type: str = Field(description="Type of sensor (gps, accelerometer, etc.)")
    value: dict[str, Any] = Field(description="Sensor reading values")
    unit: str | None = Field(default=None, description="Unit of measurement")
    accuracy: float | None = Field(default=None, description="Reading accuracy")


class GPSReading(BaseMessage):
    """GPS coordinate reading."""

    latitude: float = Field(description="Latitude in decimal degrees")
    longitude: float = Field(description="Longitude in decimal degrees")
    altitude: float | None = Field(default=None, description="Altitude in meters")
    accuracy: float | None = Field(
        default=None,
        description="GPS accuracy in meters",
    )
    heading: float | None = Field(default=None, description="Heading in degrees")
    speed: float | None = Field(default=None, description="Speed in m/s")


class AccelerometerReading(BaseMessage):
    """Accelerometer sensor reading."""

    x: float = Field(description="X-axis acceleration in m/s²")
    y: float = Field(description="Y-axis acceleration in m/s²")
    z: float = Field(description="Z-axis acceleration in m/s²")


class HeartRateReading(BaseMessage):
    """Heart rate sensor reading."""

    bpm: int = Field(description="Beats per minute")
    confidence: float | None = Field(
        default=None,
        description="Reading confidence 0-1",
    )


class PowerState(BaseMessage):
    """Device power state information."""

    battery_level: float = Field(description="Battery level percentage 0-100")
    is_charging: bool = Field(description="Whether device is charging")
    power_source: str | None = Field(default=None, description="Power source type")


class LockState(BaseMessage):
    """Device lock/unlock state information."""

    is_locked: bool = Field(description="Whether device is currently locked")
    lock_type: str | None = Field(
        default=None,
        description="Type of lock (screen, device, app, etc.)",
    )
    lock_timestamp: datetime | None = Field(
        default=None,
        description="When the lock state changed",
    )


class ImageData(BaseMessage):
    """Image data from camera or screenshot."""

    image_data: bytes = Field(description="Raw image data")
    format: str = Field(default="jpeg", description="Image format")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    camera_type: str | None = Field(
        default=None,
        description="Camera type (front/rear/screen)",
    )


class WebSocketMessage(BaseModel):
    """WebSocket message wrapper."""

    message_type: str = Field(description="Type of message (audio, sensor, etc.)")
    data: dict[str, Any] = Field(description="Message payload")


# Sprint 4: App Monitoring Models


class ApplicationInfo(BaseModel):
    """Information about a running application."""

    pid: int = Field(description="Process ID")
    name: str = Field(description="Application name")
    bundle_id: str = Field(description="Application bundle identifier")
    active: bool = Field(
        description="Whether the application is currently active/focused",
    )
    hidden: bool = Field(description="Whether the application is hidden")
    launch_date: float | None = Field(
        default=None,
        description="Application launch timestamp (Unix timestamp)",
    )

    @validator("pid")
    def validate_pid(cls, v):
        if v <= 0:
            raise ValueError("PID must be positive")
        return v

    @validator("bundle_id")
    def validate_bundle_id(cls, v):
        if not v or v.strip() == "":
            return "unknown"
        return v.strip()


class MacOSAppMonitoring(BaseMessage):
    """macOS application monitoring data."""

    running_applications: list[ApplicationInfo] = Field(
        description="List of currently running applications",
        max_items=100,  # Configurable limit
    )

    @validator("running_applications")
    def validate_app_list(cls, v):
        if len(v) > 100:  # Will be configurable via settings
            raise ValueError("Too many applications in single request")
        return v


class AndroidAppInfo(BaseModel):
    """Information about an Android application."""

    pid: int = Field(description="Process ID")
    name: str = Field(description="Application name")
    package_name: str = Field(description="Android package name")
    active: bool = Field(
        description="Whether the application is currently active/foreground",
    )
    hidden: bool = Field(description="Whether the application is hidden/background")
    launch_date: float | None = Field(
        default=None,
        description="Application launch timestamp (Unix timestamp)",
    )
    version_code: int | None = Field(
        default=None,
        description="Application version code",
    )
    version_name: str | None = Field(
        default=None,
        description="Application version name",
    )

    @validator("pid")
    def validate_pid(cls, v):
        if v <= 0:
            raise ValueError("PID must be positive")
        return v

    @validator("package_name")
    def validate_package_name(cls, v):
        if not v or v.strip() == "":
            return "unknown"
        return v.strip()


class AndroidAppMonitoring(BaseMessage):
    """Android application monitoring data."""

    running_applications: list[AndroidAppInfo] = Field(
        description="List of currently running Android applications",
        max_items=100,  # Configurable limit
    )

    @validator("running_applications")
    def validate_app_list(cls, v):
        if len(v) > 100:  # Will be configurable via settings
            raise ValueError("Too many applications in single request")
        return v


# Sprint 4: Device Metadata Models


class DeviceMetadata(BaseMessage):
    """Arbitrary device metadata storage."""

    metadata_type: str = Field(
        description="Type of metadata (device_capabilities, hardware_specs, software_config, etc.)",
    )
    metadata: dict[str, Any] = Field(
        description="Flexible metadata object containing device-specific information",
    )

    @validator("metadata_type")
    def validate_metadata_type(cls, v):
        if not v or v.strip() == "":
            raise ValueError("metadata_type cannot be empty")
        return v.strip().lower()

    @validator("metadata")
    def validate_metadata(cls, v):
        if not v:
            raise ValueError("metadata cannot be empty")
        return v


# Response Models


class APIResponse(BaseModel):
    """Standard API response."""

    status: str = Field(description="Response status (success, error)")
    message_id: str | None = Field(
        default=None,
        description="Message ID if applicable",
    )
    topic: str | None = Field(default=None, description="Kafka topic if applicable")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )


class BatchResponse(BaseModel):
    """Response for batch operations."""

    status: str = Field(description="Overall batch status")
    total: int = Field(description="Total number of items processed")
    processed: int = Field(description="Number of successfully processed items")
    failed: int = Field(description="Number of failed items")
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for failed items",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp",
    )


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy", description="Service status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Check timestamp",
    )
    version: str = Field(default="0.1.0", description="Service version")
    kafka_connected: bool = Field(description="Kafka connection status")
