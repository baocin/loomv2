"""Data models for Parakeet-TDT service."""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    recorded_at: datetime = Field(..., description="When the data was recorded")
    received_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the message was received"
    )
    schema_version: str = Field(default="1.0", description="Schema version")


class AudioChunk(BaseModel):
    """Model for VAD-filtered audio chunks from Kafka (matches VADFilteredAudio)."""

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
    
    @property
    def chunk_id(self) -> str:
        """Get chunk ID from message_id for compatibility."""
        return self.message_id or f"{self.device_id}_{int(self.recorded_at.timestamp())}"
    
    @property
    def audio_data(self) -> str:
        """Get audio data for compatibility."""
        return self.data


class TranscribedWord(BaseModel):
    """Model for a single transcribed word with timing."""

    word: str = Field(..., description="The transcribed word")
    start_time: float = Field(
        ..., description="Start time in seconds from beginning of audio"
    )
    end_time: float = Field(
        ..., description="End time in seconds from beginning of audio"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score for this word"
    )


class TranscribedText(BaseModel):
    """Model for word-by-word transcription output."""

    device_id: str = Field(..., description="Device ID")
    recorded_at: datetime = Field(..., description="UTC timestamp when recorded")
    timestamp: datetime | None = Field(None, description="Processing timestamp")
    message_id: str | None = Field(None, description="Message ID")
    trace_id: str | None = Field(None, description="Trace ID for correlation")
    services_encountered: list[str] | None = Field(None, description="Services that processed this")
    content_hash: str | None = Field(None, description="Content hash")
    
    chunk_id: str = Field(
        ..., description="ID of the audio chunk this transcript is from"
    )
    words: list[TranscribedWord] = Field(
        ..., description="List of transcribed words with timing"
    )
    text: str = Field(..., description="Full transcribed text")
    language: str = Field(default="en", description="Detected or specified language")
    processing_time_ms: float = Field(
        ..., description="Time taken to process in milliseconds"
    )
    model_version: str = Field(
        default="kyutai/stt-2.6b-en",
        description="Model used for transcription",
    )
    
    @property
    def full_text(self) -> str:
        """Get full text for compatibility."""
        return self.text
