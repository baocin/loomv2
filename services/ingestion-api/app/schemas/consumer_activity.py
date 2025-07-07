"""Models for consumer activity logging."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ConsumerActivityRequest(BaseModel):
    """Request model for logging consumer activity."""

    consumer_id: str = Field(..., description="Service name of the consumer")
    consumed_message: dict[str, Any] | None = Field(
        None,
        description="The message that was consumed",
    )
    produced_message: dict[str, Any] | None = Field(
        None,
        description="The message that was produced",
    )
    consumed_at: datetime | None = Field(
        None,
        description="When the message was consumed",
    )
    produced_at: datetime | None = Field(
        None,
        description="When the message was produced",
    )

    @validator("consumer_id")
    def validate_consumer_id(cls, v: str) -> str:
        """Ensure consumer_id is not empty."""
        if not v or not v.strip():
            raise ValueError("consumer_id cannot be empty")
        return v.strip()

    @validator("produced_at")
    def validate_produced_after_consumed(
        cls,
        produced_at: datetime | None,
        values: dict,
    ) -> datetime | None:
        """Ensure produced_at is after consumed_at if both are provided."""
        if produced_at and values.get("consumed_at"):
            if produced_at < values["consumed_at"]:
                raise ValueError("produced_at must be after consumed_at")
        return produced_at

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        schema_extra = {
            "example": {
                "consumer_id": "silero-vad",
                "consumed_message": {
                    "device_id": "550e8400-e29b-41d4-a716-446655440000",
                    "audio_data": "base64_encoded_audio",
                    "sample_rate": 16000,
                    "timestamp": "2024-01-15T10:30:00Z",
                },
                "consumed_at": "2024-01-15T10:30:01Z",
            },
        }


class ConsumerActivityLog(BaseModel):
    """Model representing a consumer activity log entry."""

    id: UUID
    consumer_id: str
    last_consumed_message: dict[str, Any] | None
    last_produced_message: dict[str, Any] | None
    message_consumed_at: datetime | None
    message_produced_at: datetime | None
    last_complete_processed_consumed_message: dict[str, Any] | None
    last_complete_processed_produced_message: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        orm_mode = True


class ConsumerActivityResponse(BaseModel):
    """Response model for consumer activity endpoints."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    data: ConsumerActivityLog | None = Field(
        None,
        description="The consumer activity log entry",
    )

    class Config:
        """Pydantic config."""

        schema_extra = {
            "example": {
                "success": True,
                "message": "Consumer activity logged successfully",
                "data": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "consumer_id": "silero-vad",
                    "last_consumed_message": {"device_id": "...", "audio_data": "..."},
                    "message_consumed_at": "2024-01-15T10:30:01Z",
                    "created_at": "2024-01-15T10:30:01Z",
                    "updated_at": "2024-01-15T10:30:01Z",
                },
            },
        }


class ConsumerActivityMonitoring(BaseModel):
    """Model for consumer activity monitoring view."""

    consumer_id: str
    flow_name: str
    flow_priority: str
    message_consumed_at: datetime | None
    message_produced_at: datetime | None
    processing_time_ms: float | None
    seconds_since_consumed: float | None
    seconds_since_produced: float | None
    last_device_id: str | None
    consumed_from_topic: str | None
    consumed_message_type: str | None
    produced_message_type: str | None
    processing_status: str
    is_inactive: bool
    is_stuck: bool

    class Config:
        """Pydantic config."""

        orm_mode = True
