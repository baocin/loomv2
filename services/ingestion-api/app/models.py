"""Pydantic models for ingestion API data structures."""

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, validator

# Python 3.10 compatibility
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc


class BaseMessage(BaseModel):
    """Base message structure for all Kafka messages."""

    schema_version: str = Field(default="1.0", description="Message schema version")
    device_id: str = Field(description="Client device identifier (UUIDv8)")
    recorded_at: datetime = Field(description="UTC timestamp when data was recorded")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when message was processed by server",
    )
    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message ID",
    )
    # Trace information fields
    trace_id: str | None = Field(
        default=None,
        description="Distributed trace ID for request correlation",
    )
    services_encountered: list[str] = Field(
        default_factory=list,
        description="List of services that have processed this message",
    )

    @validator("device_id")
    def validate_device_id(cls, v):
        """Validate device_id is a valid UUID format."""
        if not v:
            raise ValueError("device_id is required")

        # Check if it's a valid UUID format (accepts v4, v8, or any standard UUID)
        # UUIDv8 format: xxxxxxxx-xxxx-8xxx-xxxx-xxxxxxxxxxxx
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            raise ValueError(
                "device_id must be a valid UUID format (preferably UUIDv8)",
            )

        return v

    @validator("recorded_at")
    def validate_recorded_at(cls, v):
        """Validate recorded_at is a UTC timestamp."""
        if not v:
            raise ValueError("recorded_at is required")

        # Ensure timezone is UTC or add UTC if naive
        if v.tzinfo is None:
            v = v.replace(tzinfo=UTC)
        elif v.tzinfo != UTC:
            v = v.astimezone(UTC)

        return v

    @validator("timestamp", pre=True, always=True)
    def ensure_utc_timestamp(cls, v):
        """Ensure timestamp is always UTC."""
        if v is None:
            v = datetime.now(UTC)
        elif isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=UTC)
            elif v.tzinfo != UTC:
                v = v.astimezone(UTC)

        return v


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


class ImageData(BaseMessage):
    """Image data from camera or screenshot."""

    image_data: bytes = Field(description="Base64 encoded image data")
    format: str = Field(default="jpeg", description="Image format")
    width: int = Field(description="Image width in pixels")
    height: int = Field(description="Image height in pixels")
    camera_type: str | None = Field(
        default=None,
        description="Camera type (front/rear/screen)",
    )
    file_size: int | None = Field(default=None, description="File size in bytes")
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="EXIF and other image metadata",
    )


class NoteData(BaseMessage):
    """Text note or memo data."""

    content: str = Field(description="Note content text")
    title: str | None = Field(default=None, description="Optional note title")
    note_type: str = Field(
        default="text",
        description="Note type (text, markdown, code)",
    )
    tags: list[str] = Field(default_factory=list, description="Note tags")
    word_count: int | None = Field(default=None, description="Word count")
    language: str | None = Field(default=None, description="Detected language")

    @validator("content")
    def validate_content(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Note content cannot be empty")
        return v.strip()

    @validator("word_count", pre=True, always=True)
    def calculate_word_count(cls, v, values):
        if "content" in values:
            return len(values["content"].split())
        return v


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
    trace_id: str | None = Field(
        default=None,
        description="Distributed trace ID for request correlation",
    )
    services_encountered: list[str] = Field(
        default_factory=list,
        description="List of services that have processed this request",
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


class GitHubTask(BaseMessage):
    """GitHub URL processing task."""

    url: str = Field(description="GitHub URL to process")
    repository_type: str = Field(
        default="repository",
        description="Type of GitHub resource (repository, file, issue, pr)",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)",
    )
    include_files: list[str] = Field(
        default_factory=list,
        description="File patterns to include (e.g., ['*.py', '*.md'])",
    )
    exclude_files: list[str] = Field(
        default_factory=list,
        description="File patterns to exclude",
    )
    max_file_size: int = Field(
        default=1048576,  # 1MB
        description="Maximum file size in bytes",
    )
    extract_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Options for content extraction",
    )
    callback_webhook: str | None = Field(
        None,
        description="Webhook URL for processing completion notification",
    )

    @validator("url")
    def validate_github_url(cls, v):
        """Validate that URL is a GitHub URL."""
        if not v.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError("URL must be a GitHub URL")
        return v


class DocumentTask(BaseMessage):
    """Document upload and processing task."""

    filename: str = Field(description="Original filename")
    file_data: str = Field(description="Base64 encoded file content")
    content_type: str = Field(
        default="application/octet-stream",
        description="MIME type of the file",
    )
    file_size: int = Field(description="File size in bytes")
    document_type: str = Field(
        default="general",
        description="Type of document (pdf, docx, txt, markdown, html)",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)",
    )
    extract_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Options for content extraction",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata",
    )
    callback_webhook: str | None = Field(
        None,
        description="Webhook URL for processing completion notification",
    )

    @validator("file_data")
    def validate_file_data(cls, v):
        """Validate base64 encoded file data."""
        if not v:
            raise ValueError("file_data is required")
        try:
            import base64

            base64.b64decode(v)
        except Exception:
            raise ValueError("file_data must be valid base64 encoded content")
        return v

    @validator("file_size")
    def validate_file_size(cls, v):
        """Validate file size is reasonable."""
        if v <= 0:
            raise ValueError("file_size must be positive")
        if v > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("file_size exceeds maximum limit of 100MB")
        return v
