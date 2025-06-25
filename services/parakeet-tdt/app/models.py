"""Data models for Parakeet-TDT service."""

from datetime import datetime

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    recorded_at: datetime = Field(..., description="When the data was recorded")
    received_at: datetime = Field(default_factory=datetime.utcnow, description="When the message was received")
    schema_version: str = Field(default="1.0", description="Schema version")


class AudioChunk(BaseMessage):
    """Model for VAD-filtered audio chunks from Kafka."""

    audio_data: str = Field(..., description="Base64-encoded audio data")
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    format: str = Field(default="wav", description="Audio format")
    duration_seconds: float = Field(..., description="Duration of audio chunk in seconds")
    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    sequence_number: int = Field(..., description="Sequence number for ordering chunks")


class TranscribedWord(BaseModel):
    """Model for a single transcribed word with timing."""

    word: str = Field(..., description="The transcribed word")
    start_time: float = Field(..., description="Start time in seconds from beginning of audio")
    end_time: float = Field(..., description="End time in seconds from beginning of audio")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this word")


class TranscribedText(BaseMessage):
    """Model for word-by-word transcription output."""

    chunk_id: str = Field(..., description="ID of the audio chunk this transcript is from")
    words: list[TranscribedWord] = Field(..., description="List of transcribed words with timing")
    full_text: str = Field(..., description="Full transcribed text")
    language: str = Field(default="en", description="Detected or specified language")
    processing_time_ms: float = Field(..., description="Time taken to process in milliseconds")
    model_version: str = Field(
        default="nvidia/parakeet-tdt_ctc-1.1b",
        description="Model used for transcription",
    )
