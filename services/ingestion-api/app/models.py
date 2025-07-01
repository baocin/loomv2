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
    UTC = UTC


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
            msg = "device_id is required"
            raise ValueError(msg)

        # Check if it's a valid UUID format (accepts v4, v8, or any standard UUID)
        # UUIDv8 format: xxxxxxxx-xxxx-8xxx-xxxx-xxxxxxxxxxxx
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        if not uuid_pattern.match(v):
            msg = "device_id must be a valid UUID format (preferably UUIDv8)"
            raise ValueError(msg)

        return v

    @validator("recorded_at")
    def validate_recorded_at(cls, v):
        """Validate recorded_at is a UTC timestamp."""
        if not v:
            msg = "recorded_at is required"
            raise ValueError(msg)

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
    lid_closed: bool | None = Field(
        default=None,
        description="Whether laptop lid is closed",
    )
    thermal_state: str | None = Field(
        default=None,
        description="Thermal state (nominal, fair, serious, critical)",
    )


class NetworkWiFiReading(BaseMessage):
    """WiFi network information."""

    ssid: str = Field(description="Network SSID")
    bssid: str | None = Field(default=None, description="Access point MAC address")
    signal_strength: int = Field(description="Signal strength in dBm")
    frequency: float | None = Field(default=None, description="Frequency in MHz")
    channel: int | None = Field(default=None, description="WiFi channel")
    security: str | None = Field(
        default=None,
        description="Security type (WPA2, WPA3, etc.)",
    )
    connected: bool = Field(default=False, description="Whether currently connected")
    ip_address: str | None = Field(
        default=None,
        description="Local IP address if connected",
    )


class NetworkBluetoothReading(BaseMessage):
    """Bluetooth device detection."""

    device_name: str = Field(description="Bluetooth device name")
    device_address: str = Field(description="Bluetooth MAC address")
    device_type: str | None = Field(
        default=None,
        description="Device type (headphones, keyboard, etc.)",
    )
    rssi: int | None = Field(
        default=None,
        description="Received signal strength indicator",
    )
    connected: bool = Field(default=False, description="Whether currently connected")
    paired: bool = Field(default=False, description="Whether device is paired")


class TemperatureReading(BaseMessage):
    """Temperature sensor reading."""

    temperature: float = Field(description="Temperature value")
    unit: str = Field(
        default="celsius",
        description="Temperature unit (celsius, fahrenheit)",
    )
    sensor_location: str | None = Field(
        default=None,
        description="Sensor location (cpu, battery, ambient, etc.)",
    )


class BarometerReading(BaseMessage):
    """Barometric pressure reading."""

    pressure: float = Field(description="Atmospheric pressure")
    unit: str = Field(default="hPa", description="Pressure unit (hPa, inHg, mmHg)")
    altitude: float | None = Field(
        default=None,
        description="Calculated altitude in meters",
    )


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


# Android App Usage Statistics (Pre-aggregated from UsageStats API)


class AndroidAppUsageStats(BaseModel):
    """Pre-aggregated app usage statistics from Android UsageStats API."""

    package_name: str = Field(description="Android package name")
    app_name: str | None = Field(default=None, description="Human-readable app name")
    total_time_foreground_ms: int = Field(
        description="Total time app was in foreground (milliseconds)",
    )
    last_time_used: datetime = Field(description="Last time the app was used")
    last_time_foreground_service_used: datetime | None = Field(
        default=None,
        description="Last time app's foreground service was used",
    )
    total_time_foreground_service_used_ms: int = Field(
        default=0,
        description="Total time foreground service was used (milliseconds)",
    )
    launch_count: int = Field(default=0, description="Number of times app was launched")


class AndroidAppEventStats(BaseModel):
    """App event statistics from Android UsageEvents."""

    package_name: str = Field(description="Android package name")
    event_type: str = Field(
        description="Event type (MOVE_TO_FOREGROUND, MOVE_TO_BACKGROUND, etc.)",
    )
    event_count: int = Field(description="Number of times this event occurred")
    last_event_time: datetime = Field(description="Last time this event occurred")


class AndroidScreenTimeStats(BaseModel):
    """Screen time statistics aggregated by category or app."""

    category: str = Field(
        description="App category (SOCIAL, PRODUCTIVITY, GAME, etc.)",
    )
    total_time_ms: int = Field(description="Total screen time in milliseconds")
    app_count: int = Field(description="Number of apps in this category")
    percentage_of_total: float = Field(
        description="Percentage of total screen time",
        ge=0,
        le=100,
    )


class AndroidNotificationStats(BaseModel):
    """Notification statistics per app."""

    package_name: str = Field(description="Android package name")
    notification_count: int = Field(description="Total notifications received")
    interaction_count: int = Field(
        default=0,
        description="Number of notifications interacted with",
    )
    dismissal_count: int = Field(
        default=0,
        description="Number of notifications dismissed",
    )


class AndroidAppUsageAggregated(BaseMessage):
    """Pre-aggregated Android app usage data."""

    aggregation_period_start: datetime = Field(
        description="Start of aggregation period",
    )
    aggregation_period_end: datetime = Field(description="End of aggregation period")
    aggregation_interval_minutes: int = Field(
        default=60,
        description="Aggregation interval in minutes",
    )
    total_screen_time_ms: int = Field(
        description="Total screen time during period (milliseconds)",
    )
    total_unlocks: int = Field(default=0, description="Number of device unlocks")
    app_usage_stats: list[AndroidAppUsageStats] = Field(
        description="Per-app usage statistics",
        max_items=500,
    )
    app_event_stats: list[AndroidAppEventStats] = Field(
        default_factory=list,
        description="App event statistics",
        max_items=1000,
    )
    screen_time_by_category: list[AndroidScreenTimeStats] = Field(
        default_factory=list,
        description="Screen time grouped by app category",
    )
    notification_stats: list[AndroidNotificationStats] = Field(
        default_factory=list,
        description="Notification statistics per app",
        max_items=200,
    )

    @validator("aggregation_period_end")
    def validate_period(cls, v, values):
        if "aggregation_period_start" in values:
            if v <= values["aggregation_period_start"]:
                raise ValueError("End time must be after start time")
        return v

    @validator("app_usage_stats")
    def validate_usage_stats(cls, v):
        if len(v) > 500:
            raise ValueError("Too many app usage entries")
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


# OS Event Models


class OSEventAppLifecycle(BaseMessage):
    """OS application lifecycle event."""

    app_identifier: str = Field(description="Application identifier (package name or bundle ID)")
    app_name: str | None = Field(default=None, description="Human-readable application name")
    event_type: str = Field(
        description="Event type",
        pattern="^(launch|foreground|background|terminate|crash)$",
    )
    duration_seconds: int | None = Field(
        default=None,
        description="Duration in seconds (for background/foreground events)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata",
    )


class OSEventSystemRaw(BaseMessage):
    """OS system event (power, screen, lock, etc.)."""

    event_type: str = Field(
        description="System event type (e.g., screen_on, screen_off, device_lock, device_unlock, power_connected, power_disconnected)",
    )
    event_category: str = Field(
        default="system",
        description="Event category (system, power, screen, lock)",
    )
    severity: str = Field(
        default="info",
        description="Event severity (info, warning, error)",
        pattern="^(info|warning|error)$",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable event description",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event metadata",
    )

    @validator("event_type")
    def validate_event_type(cls, v):
        """Validate that event_type is not empty."""
        if not v or v.strip() == "":
            raise ValueError("event_type cannot be empty")
        return v.strip().lower()


class OSEventNotification(BaseMessage):
    """OS notification event."""

    notification_id: str = Field(description="Unique notification identifier")
    app_identifier: str = Field(description="Application identifier that sent the notification")
    title: str | None = Field(default=None, description="Notification title")
    body: str | None = Field(default=None, description="Notification body text")
    action: str | None = Field(
        default=None,
        description="Action taken on notification (posted, removed, clicked)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional notification metadata",
    )


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
