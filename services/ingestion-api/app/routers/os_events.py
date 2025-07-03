"""OS event endpoints for system events, app lifecycle, and notifications."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..auth import verify_api_key
from ..config import settings
from ..kafka_producer import kafka_producer
from ..models import (
    APIResponse,
    OSEventAppLifecycle,
    OSEventNotification,
    OSEventSystemRaw,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/os-events", tags=["os-events"])


@router.post(
    "/app-lifecycle",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_app_lifecycle_event(
    event: OSEventAppLifecycle,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Upload OS application lifecycle event.

    This endpoint accepts events about application lifecycle changes including:
    - App launch
    - App moved to foreground
    - App moved to background
    - App termination
    - App crash

    Args:
    ----
        event: Application lifecycle event data

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If Kafka publishing fails

    """
    try:
        # Send to Kafka
        await kafka_producer.send_message(
            topic="os.events.app_lifecycle.raw",
            key=event.device_id,
            message=event,
        )

        logger.info(
            "App lifecycle event sent to Kafka",
            device_id=event.device_id,
            app_identifier=event.app_identifier,
            event_type=event.event_type,
            message_id=event.message_id,
            topic="os.events.app_lifecycle.raw",
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": event.message_id,
                "topic": "os.events.app_lifecycle.raw",
                "event_type": event.event_type,
                "app_identifier": event.app_identifier,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to process app lifecycle event",
            device_id=event.device_id,
            app_identifier=event.app_identifier,
            event_type=event.event_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process app lifecycle event: {e!s}",
        )


@router.post(
    "/system",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_system_event(
    event: OSEventSystemRaw,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Upload OS system event.

    This endpoint accepts system-level events including:
    - Screen on/off events
    - Device lock/unlock events
    - Power connection/disconnection
    - Other system events

    Args:
    ----
        event: System event data

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If Kafka publishing fails

    """
    try:
        # Send to Kafka
        await kafka_producer.send_message(
            topic="os.events.system.raw",
            key=event.device_id,
            message=event,
        )

        logger.info(
            "System event sent to Kafka",
            device_id=event.device_id,
            event_type=event.event_type,
            event_category=event.event_category,
            message_id=event.message_id,
            topic="os.events.system.raw",
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": event.message_id,
                "topic": "os.events.system.raw",
                "event_type": event.event_type,
                "event_category": event.event_category,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to process system event",
            device_id=event.device_id,
            event_type=event.event_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process system event: {e!s}",
        )


@router.post(
    "/notifications",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_notification_event(
    event: OSEventNotification,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Upload OS notification event.

    This endpoint accepts notification events including:
    - Notification posted
    - Notification removed
    - Notification clicked/interacted with

    Args:
    ----
        event: Notification event data

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If Kafka publishing fails

    """
    try:
        # Send to Kafka
        await kafka_producer.send_message(
            topic="os.events.notifications.raw",
            key=event.device_id,
            message=event,
        )

        logger.info(
            "Notification event sent to Kafka",
            device_id=event.device_id,
            notification_id=event.notification_id,
            app_identifier=event.app_identifier,
            action=event.action,
            message_id=event.message_id,
            topic="os.events.notifications.raw",
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": event.message_id,
                "topic": "os.events.notifications.raw",
                "notification_id": event.notification_id,
                "action": event.action,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to process notification event",
            device_id=event.device_id,
            notification_id=event.notification_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process notification event: {e!s}",
        )


@router.get("/event-types", status_code=status.HTTP_200_OK)
async def get_os_event_types() -> JSONResponse:
    """Get supported OS event types and their descriptions.

    Returns information about supported event types for each category.

    Returns
    -------
        Dictionary of supported event types with descriptions

    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "app_lifecycle": {
                "description": "Application lifecycle events",
                "event_types": {
                    "launch": "Application was launched",
                    "foreground": "Application moved to foreground",
                    "background": "Application moved to background",
                    "terminate": "Application was terminated",
                    "crash": "Application crashed",
                },
                "topic": "os.events.app_lifecycle.raw",
            },
            "system": {
                "description": "System-level events",
                "event_types": {
                    "screen_on": "Device screen turned on",
                    "screen_off": "Device screen turned off",
                    "device_lock": "Device was locked",
                    "device_unlock": "Device was unlocked",
                    "power_connected": "Power/charger connected",
                    "power_disconnected": "Power/charger disconnected",
                    "boot_completed": "Device boot completed",
                    "shutdown": "Device shutdown initiated",
                },
                "event_categories": ["system", "power", "screen", "lock"],
                "topic": "os.events.system.raw",
            },
            "notifications": {
                "description": "Notification events",
                "actions": {
                    "posted": "Notification was posted/displayed",
                    "removed": "Notification was removed",
                    "clicked": "Notification was clicked/interacted with",
                },
                "topic": "os.events.notifications.raw",
            },
        },
    )
