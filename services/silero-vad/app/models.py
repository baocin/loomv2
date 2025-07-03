"""Data models for Silero VAD service."""

import base64
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )


# Legacy AudioData model - kept for backward compatibility
class AudioData(BaseModel):
    """Legacy nested audio data structure."""
    audio_data: str = Field(..., description="Base64 encoded audio data")
    format: str = Field(..., description="Audio format")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    bits_per_sample: int = Field(..., description="Bits per sample")
    duration_ms: float = Field(..., description="Duration in milliseconds")
    device_info: dict[str, Any] | None = Field(None, description="Device information")

    @field_validator("audio_data")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        """Validate that audio_data is valid base64."""
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("Invalid base64 encoding for audio_data")
        return v


class AudioChunk(BaseModel):
    """Audio chunk model matching device.audio.raw schema from ingestion API."""

    device_id: str = Field(..., description="Device ID")
    recorded_at: datetime = Field(..., description="UTC timestamp when recorded")
    timestamp: datetime | None = Field(None, description="Processing timestamp")
    message_id: str | None = Field(None, description="Message ID")
    trace_id: str | None = Field(None, description="Trace ID for correlation")
    services_encountered: list[str] | None = Field(None, description="Services that processed this")
    content_hash: str | None = Field(None, description="Content hash")
    data: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    format: str = Field(default="wav", description="Audio format")
    duration_ms: int = Field(..., description="Chunk duration in milliseconds")
    file_id: str | None = Field(None, description="Associated file ID")

    @model_validator(mode="before")
    @classmethod
    def handle_chunk_data_alias(cls, data: Any) -> Any:
        """Handle chunk_data as an alias for data field."""
        if isinstance(data, dict):
            if "chunk_data" in data and "data" not in data:
                data["data"] = data.pop("chunk_data")
        return data

    def decode_audio(self) -> bytes:
        """Decode base64 audio data to bytes."""
        return base64.b64decode(self.data)


class VADFilteredAudio(BaseModel):
    """VAD filtered audio chunk for media.audio.vad_filtered topic."""

    device_id: str = Field(..., description="Device ID")
    recorded_at: datetime = Field(..., description="UTC timestamp when recorded")
    timestamp: datetime | None = Field(None, description="Processing timestamp")
    message_id: str | None = Field(None, description="Message ID")
    trace_id: str | None = Field(None, description="Trace ID for correlation")
    services_encountered: list[str] | None = Field(None, description="Services that processed this")
    content_hash: str | None = Field(None, description="Content hash")
    data: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    format: str = Field(default="wav", description="Audio format")
    duration_ms: int = Field(..., description="Chunk duration in milliseconds")
    file_id: str | None = Field(None, description="Associated file ID")
    # VAD specific fields
    start_ms: float = Field(..., description="Start time of speech segment in ms")
    end_ms: float = Field(..., description="End time of speech segment in ms") 
    confidence: float = Field(..., description="VAD confidence score (0-1)")
    vad_threshold: float = Field(..., description="VAD threshold used")

    def encode_audio(self, audio_bytes: bytes) -> None:
        """Encode audio bytes to base64."""
        self.data = base64.b64encode(audio_bytes).decode("utf-8")
