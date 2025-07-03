"""Unified data ingestion endpoint with message type mapping."""

import base64
from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["unified-ingestion"])


class UnifiedMessage(BaseModel):
    """Unified message structure for all data types."""

    message_type_id: str = Field(description="Message type ID that maps to Kafka topic")
    device_id: str = Field(description="Device identifier")
    data: Dict[str, Any] = Field(description="Message data payload")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata"
    )


# Message type to Kafka topic mapping
# Topics handle routing - Kafka consumer groups handle duplication/distribution
MESSAGE_TYPE_MAPPINGS = {
    # Device data types
    "audio_chunk": "device.audio.raw",
    "gps_reading": "device.sensor.gps.raw",
    "accelerometer": "device.sensor.accelerometer.raw",
    "heartrate": "device.health.heartrate.raw",
    "power_state": "device.state.power.raw",
    "wifi_state": "device.network.wifi.raw",
    "bluetooth_scan": "device.network.bluetooth.raw",
    "temperature": "device.sensor.temperature.raw",
    "barometer": "device.sensor.barometer.raw",
    "device_metadata": "device.metadata.raw",
    # Image/Video types
    "camera_photo": "device.image.camera.raw",
    "screenshot": "device.video.screen.raw",  # General screenshots - direct to storage
    "twitter_screenshot": "external.twitter.images.raw",  # Twitter/X screenshots - to OCR pipeline
    # OS Events
    "app_lifecycle": "os.events.app_lifecycle.raw",
    "system_event": "os.events.system.raw",
    "notification": "os.events.notifications.raw",
    # System monitoring
    "macos_apps": "device.system.apps.macos.raw",
    "android_apps": "device.system.apps.android.raw",
    # Digital content
    "digital_note": "digital.notes.raw",
    "clipboard": "digital.clipboard.raw",
    # External sources
    "twitter_liked": "external.twitter.liked.raw",
    "email_event": "external.email.events.raw",
    "calendar_event": "external.calendar.events.raw",
    # Tasks
    "url_to_process": "task.url.ingest",
}

# Pipeline hints for consumers to understand processing intent
PIPELINE_HINTS = {
    "audio_chunk": "audio_transcription",  # VAD → STT → Text
    "twitter_screenshot": "ocr_extraction",  # OCR → Analysis
    "camera_photo": "direct_storage",  # No processing needed
    "screenshot": "direct_storage",  # No processing needed
}


# Validation rules for different message types
MESSAGE_TYPE_VALIDATIONS = {
    "screenshot": {
        "required_fields": ["image_data", "width", "height"],
        "validate_base64": ["image_data"],
    },
    "twitter_screenshot": {
        "required_fields": ["image_data", "width", "height"],
        "validate_base64": ["image_data"],
    },
    "camera_photo": {
        "required_fields": ["image_data", "width", "height"],
        "validate_base64": ["image_data"],
    },
    "audio_chunk": {
        "required_fields": ["chunk_data", "sample_rate", "duration_ms"],
        "validate_base64": ["chunk_data"],
    },
    "gps_reading": {"required_fields": ["latitude", "longitude"]},
    "accelerometer": {"required_fields": ["x", "y", "z"]},
    # Add more validations as needed
}


def validate_message_data(message_type_id: str, data: Dict[str, Any]) -> None:
    """Validate message data based on type."""
    if message_type_id not in MESSAGE_TYPE_VALIDATIONS:
        return  # No specific validation rules

    rules = MESSAGE_TYPE_VALIDATIONS[message_type_id]

    # Check required fields
    if "required_fields" in rules:
        for field in rules["required_fields"]:
            if field not in data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field '{field}' for message type '{message_type_id}'",
                )

    # Validate base64 fields
    if "validate_base64" in rules:
        for field in rules["validate_base64"]:
            if field in data:
                try:
                    base64.b64decode(data[field])
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid base64 data in field '{field}'",
                    )


@router.post("/message")
async def ingest_unified_message(
    message: UnifiedMessage,
    api_key: str = Depends(verify_api_key),
) -> Dict[str, Any]:
    """Unified endpoint for all data ingestion.

    Args:
        message: Unified message with type ID and data

    Returns:
        Response with status and routing information
    """
    try:
        # Validate message type
        if message.message_type_id not in MESSAGE_TYPE_MAPPINGS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown message type: {message.message_type_id}. "
                f"Valid types: {list(MESSAGE_TYPE_MAPPINGS.keys())}",
            )

        # Get target topic
        topic = MESSAGE_TYPE_MAPPINGS[message.message_type_id]

        # Validate message data
        validate_message_data(message.message_type_id, message.data)

        # Get pipeline hint if available
        pipeline_hint = PIPELINE_HINTS.get(message.message_type_id)

        # Create standardized message for Kafka
        kafka_message = {
            "schema_version": "1.0",
            "device_id": message.device_id,
            "message_type": message.message_type_id,
            "data": message.data,
            "metadata": message.metadata,
            "timestamp": None,  # Will be set by kafka_producer
        }

        # Add pipeline hint if available (helps consumers understand processing intent)
        if pipeline_hint:
            kafka_message["pipeline_hint"] = pipeline_hint

        # Send to appropriate Kafka topic
        await kafka_producer.send_message(
            topic=topic,
            message=kafka_message,
        )

        logger.info(
            "Unified message ingested successfully",
            device_id=message.device_id,
            message_type=message.message_type_id,
            topic=topic,
            data_keys=list(message.data.keys()),
        )

        return {
            "status": "success",
            "message_type": message.message_type_id,
            "topic": topic,
            "timestamp": kafka_message.get("timestamp"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to ingest unified message",
            device_id=message.device_id,
            message_type=message.message_type_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to ingest message")


@router.get("/message-types")
async def get_message_types() -> Dict[str, str]:
    """Get available message types and their target topics."""
    return MESSAGE_TYPE_MAPPINGS


@router.get("/message-types/{message_type_id}")
async def get_message_type_info(message_type_id: str) -> Dict[str, Any]:
    """Get information about a specific message type."""
    if message_type_id not in MESSAGE_TYPE_MAPPINGS:
        raise HTTPException(status_code=404, detail="Message type not found")

    return {
        "message_type_id": message_type_id,
        "topic": MESSAGE_TYPE_MAPPINGS[message_type_id],
        "pipeline_hint": PIPELINE_HINTS.get(message_type_id),
        "validation_rules": MESSAGE_TYPE_VALIDATIONS.get(message_type_id, {}),
    }
