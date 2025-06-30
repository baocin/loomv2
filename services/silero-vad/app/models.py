"""Data models for Silero VAD service."""

import base64
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata"
    )


class AudioData(BaseModel):
    """Nested audio data structure."""
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
    """Audio chunk model matching device.audio.raw schema."""

    schema_version: str = Field(..., description="Schema version")
    device_id: str = Field(..., description="Device ID")
    timestamp: datetime = Field(..., description="UTC timestamp when the chunk was captured")
    trace_id: str = Field(..., description="Trace ID for correlation")
    data: AudioData = Field(..., description="Nested audio data")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    def decode_audio(self) -> bytes:
        """Decode base64 audio data to bytes."""
        return base64.b64decode(self.data.audio_data)


class VADFilteredAudio(BaseModel):
    """VAD filtered audio chunk for media.audio.vad_filtered topic."""

    schema_version: str = Field(default="1.0.0", description="Schema version")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp when the audio was captured")
    device_id: str = Field(..., description="Unique identifier for the device")
    file_id: str = Field(..., description="Unique identifier for the audio file/stream")
    chunk_index: int = Field(..., description="Sequential index of this chunk within the file")
    audio_data: str = Field(..., description="Base64 encoded audio data")
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    duration_ms: int = Field(..., description="Duration of audio chunk in milliseconds")
    vad_confidence: float = Field(..., description="VAD confidence score (0-1)")
    speech_probability: float | None = Field(None, description="Probability that chunk contains speech")

    def encode_audio(self, audio_bytes: bytes) -> None:
        """Encode audio bytes to base64."""
        self.audio_data = base64.b64encode(audio_bytes).decode("utf-8")
