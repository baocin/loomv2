"""Data models for Parakeet-TDT service."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class BaseMessage(BaseModel):
    """Base message model with common fields."""

    device_id: str = Field(..., description="Unique device identifier")
    recorded_at: datetime = Field(..., description="When the data was recorded")
    received_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the message was received"
    )
    schema_version: str = Field(default="1.0", description="Schema version")


class AudioChunk(BaseModel):
    """Model for raw audio chunks from Kafka (matches ingestion API AudioChunk)."""

    # Required fields with flexible names
    device_id: str = Field(..., description="Device ID")
    recorded_at: datetime = Field(..., description="UTC timestamp when recorded")
    
    # Optional fields
    timestamp: datetime | None = Field(None, description="Processing timestamp")
    message_id: str | None = Field(None, description="Message ID")
    trace_id: str | None = Field(None, description="Trace ID for correlation")
    services_encountered: list[str] | None = Field(None, description="Services that processed this")
    content_hash: str | None = Field(None, description="Content hash")
    
    # Audio data - flexible field names
    data: str | None = Field(None, description="Base64 encoded audio data")
    audio_data: str | None = Field(None, description="Base64 encoded audio data (legacy)")
    
    # Audio metadata
    sample_rate: int = Field(..., description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    format: str = Field(default="wav", description="Audio format")
    
    # Duration - flexible field names
    duration_ms: int | None = Field(None, description="Chunk duration in milliseconds")
    duration_seconds: float | None = Field(None, description="Chunk duration in seconds (legacy)")
    
    # Other fields
    file_id: str | None = Field(None, description="Associated file ID")
    chunk_id: str | None = Field(None, description="Chunk ID (legacy)")
    sequence_number: int | None = Field(None, description="Sequence number (legacy)")
    
    @model_validator(mode='before')
    @classmethod
    def handle_field_aliases(cls, data: Any) -> Any:
        """Handle field aliases for backward compatibility."""
        if isinstance(data, dict):
            # Handle chunk_data -> data alias
            if 'chunk_data' in data and 'data' not in data and 'audio_data' not in data:
                data['data'] = data.pop('chunk_data')
            
            # Ensure we have either data or audio_data
            if 'data' not in data and 'audio_data' not in data:
                # Try to find audio data in other possible field names
                for field in ['chunk_data', 'audio']:
                    if field in data:
                        data['data'] = data.pop(field)
                        break
            
            # If we have data but not audio_data, copy it
            if 'data' in data and 'audio_data' not in data:
                data['audio_data'] = data['data']
            elif 'audio_data' in data and 'data' not in data:
                data['data'] = data['audio_data']
            
            # Handle duration conversion
            if 'duration_ms' not in data and 'duration_seconds' not in data:
                # Look for duration in other fields
                if 'duration' in data:
                    # Assume it's in milliseconds if it's > 1000, otherwise seconds
                    duration_val = data.pop('duration')
                    if duration_val > 1000:
                        data['duration_ms'] = int(duration_val)
                    else:
                        data['duration_seconds'] = float(duration_val)
            
            # Ensure we have duration_ms
            if 'duration_seconds' in data and 'duration_ms' not in data:
                data['duration_ms'] = int(data['duration_seconds'] * 1000)
            elif 'duration_ms' not in data and 'duration_seconds' not in data:
                # Default to 5 seconds if no duration specified
                data['duration_ms'] = 5000
                
            # Handle chunk_id -> message_id alias
            if 'chunk_id' in data and 'message_id' not in data:
                data['message_id'] = data['chunk_id']
                
        return data
    
    @model_validator(mode='after')
    def validate_required_fields(self) -> 'AudioChunk':
        """Ensure we have the required audio data."""
        if not self.data and not self.audio_data:
            raise ValueError("Either 'data' or 'audio_data' field is required")
        
        if not self.duration_ms and not self.duration_seconds:
            raise ValueError("Either 'duration_ms' or 'duration_seconds' field is required")
            
        return self
    
    def get_chunk_id(self) -> str:
        """Get chunk ID from available fields."""
        return self.chunk_id or self.message_id or f"{self.device_id}_{int(self.recorded_at.timestamp())}"
    
    def get_audio_data(self) -> str:
        """Get audio data from available fields."""
        return self.data or self.audio_data or ""
    
    def get_duration_seconds(self) -> float:
        """Get duration in seconds from available fields."""
        if self.duration_seconds is not None:
            return self.duration_seconds
        elif self.duration_ms is not None:
            return self.duration_ms / 1000.0
        else:
            return 5.0  # Default 5 seconds
    
    def get_duration_ms(self) -> int:
        """Get duration in milliseconds from available fields."""
        if self.duration_ms is not None:
            return self.duration_ms
        elif self.duration_seconds is not None:
            return int(self.duration_seconds * 1000)
        else:
            return 5000  # Default 5000ms


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
