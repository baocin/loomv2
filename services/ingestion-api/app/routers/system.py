"""System monitoring endpoints for app monitoring and device metadata."""

import json

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import settings
from ..kafka_producer import kafka_producer
from ..models import (
    AndroidAppMonitoring,
    APIResponse,
    DeviceMetadata,
    MacOSAppMonitoring,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.post(
    "/apps/macos",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_macos_app_monitoring(app_data: MacOSAppMonitoring) -> JSONResponse:
    """Upload macOS application monitoring data.

    This endpoint accepts data about currently running applications on macOS systems,
    including process information, bundle IDs, and application states.

    Args:
    ----
        app_data: macOS application monitoring data containing list of running apps

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If app monitoring is disabled or Kafka publishing fails

    """
    if not settings.app_monitoring_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="App monitoring is currently disabled",
        )

    try:
        # Validate app count against configuration
        if (
            len(app_data.running_applications)
            > settings.app_monitoring_max_apps_per_request
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many applications in request. Maximum allowed: {settings.app_monitoring_max_apps_per_request}",
            )

        # Convert to JSON for Kafka
        message_data = app_data.model_dump()
        message_json = json.dumps(message_data, default=str)

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_system_apps_macos,
            key=app_data.device_id,
            value=message_json,
        )

        logger.info(
            "macOS app monitoring data sent to Kafka",
            device_id=app_data.device_id,
            app_count=len(app_data.running_applications),
            message_id=app_data.message_id,
            topic=settings.topic_device_system_apps_macos,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": app_data.message_id,
                "topic": settings.topic_device_system_apps_macos,
                "app_count": len(app_data.running_applications),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process macOS app monitoring data",
            device_id=app_data.device_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process app monitoring data: {e!s}",
        )


@router.post(
    "/apps/android",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_android_app_monitoring(app_data: AndroidAppMonitoring) -> JSONResponse:
    """Upload Android application monitoring data.

    This endpoint accepts data about currently running applications on Android systems,
    including process information, package names, and application states.

    Args:
    ----
        app_data: Android application monitoring data containing list of running apps

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If app monitoring is disabled or Kafka publishing fails

    """
    if not settings.app_monitoring_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="App monitoring is currently disabled",
        )

    try:
        # Validate app count against configuration
        if (
            len(app_data.running_applications)
            > settings.app_monitoring_max_apps_per_request
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many applications in request. Maximum allowed: {settings.app_monitoring_max_apps_per_request}",
            )

        # Convert to JSON for Kafka
        message_data = app_data.model_dump()
        message_json = json.dumps(message_data, default=str)

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_system_apps_android,
            key=app_data.device_id,
            value=message_json,
        )

        logger.info(
            "Android app monitoring data sent to Kafka",
            device_id=app_data.device_id,
            app_count=len(app_data.running_applications),
            message_id=app_data.message_id,
            topic=settings.topic_device_system_apps_android,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": app_data.message_id,
                "topic": settings.topic_device_system_apps_android,
                "app_count": len(app_data.running_applications),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process Android app monitoring data",
            device_id=app_data.device_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process app monitoring data: {e!s}",
        )


@router.get("/apps/stats", status_code=status.HTTP_200_OK)
async def get_app_monitoring_stats() -> JSONResponse:
    """Get application monitoring statistics and configuration.

    Returns current configuration and runtime statistics for app monitoring endpoints.

    Returns
    -------
        Statistics about app monitoring configuration and usage

    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "app_monitoring_enabled": settings.app_monitoring_enabled,
            "max_apps_per_request": settings.app_monitoring_max_apps_per_request,
            "supported_platforms": ["macos", "android"],
            "topics": {
                "macos": settings.topic_device_system_apps_macos,
                "android": settings.topic_device_system_apps_android,
            },
        },
    )


# Device Metadata Endpoints


@router.post(
    "/metadata",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_device_metadata(metadata: DeviceMetadata) -> JSONResponse:
    """Upload arbitrary device metadata.

    This endpoint accepts flexible metadata about devices, allowing storage of
    device capabilities, hardware specifications, software configurations, and
    custom attributes.

    Args:
    ----
        metadata: Device metadata containing type and flexible metadata object

    Returns:
    -------
        API response with message ID and topic information

    Raises:
    ------
        HTTPException: If metadata validation fails or Kafka publishing fails

    """
    try:
        # Additional validation for metadata size
        metadata_json = json.dumps(metadata.metadata, default=str)
        if len(metadata_json) > 1024 * 1024:  # 1MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Metadata object too large. Maximum size: 1MB",
            )

        # Convert to JSON for Kafka
        message_data = metadata.model_dump()
        message_json = json.dumps(message_data, default=str)

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_metadata,
            key=metadata.device_id,
            value=message_json,
        )

        logger.info(
            "Device metadata sent to Kafka",
            device_id=metadata.device_id,
            metadata_type=metadata.metadata_type,
            message_id=metadata.message_id,
            topic=settings.topic_device_metadata,
            metadata_size=len(metadata_json),
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": metadata.message_id,
                "topic": settings.topic_device_metadata,
                "metadata_type": metadata.metadata_type,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process device metadata",
            device_id=metadata.device_id,
            metadata_type=metadata.metadata_type,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process device metadata: {e!s}",
        )


@router.get("/metadata/types", status_code=status.HTTP_200_OK)
async def get_metadata_types() -> JSONResponse:
    """Get supported metadata types and their descriptions.

    Returns information about common metadata types that can be stored,
    along with example structures for each type.

    Returns
    -------
        Dictionary of supported metadata types with descriptions and examples

    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "supported_types": {
                "device_capabilities": {
                    "description": "Device hardware and software capabilities",
                    "example": {
                        "sensors": ["accelerometer", "gyroscope", "gps"],
                        "cameras": {
                            "front": True,
                            "rear": True,
                            "resolution": "1920x1080",
                        },
                        "audio": {
                            "microphone": True,
                            "speakers": True,
                            "sample_rates": [44100, 48000],
                        },
                        "connectivity": ["wifi", "bluetooth", "cellular"],
                    },
                },
                "hardware_specs": {
                    "description": "Hardware specifications and technical details",
                    "example": {
                        "cpu": {"model": "Apple M1", "cores": 8, "frequency": "3.2GHz"},
                        "memory": {"total_gb": 16, "type": "LPDDR4X"},
                        "storage": {"total_gb": 512, "type": "NVMe SSD"},
                        "display": {"resolution": "2560x1600", "size_inches": 13.3},
                    },
                },
                "software_config": {
                    "description": "Software configuration and environment settings",
                    "example": {
                        "os": {"name": "macOS", "version": "14.5", "build": "23F79"},
                        "runtime": {
                            "python_version": "3.11.5",
                            "node_version": "18.17.0",
                        },
                        "timezone": "America/Los_Angeles",
                        "locale": "en_US",
                    },
                },
                "network_info": {
                    "description": "Network configuration and connectivity details",
                    "example": {
                        "wifi": {
                            "ssid": "MyNetwork",
                            "signal_strength": -45,
                            "frequency": "5GHz",
                        },
                        "cellular": {
                            "carrier": "Verizon",
                            "signal_strength": -85,
                            "technology": "5G",
                        },
                        "ip_addresses": {
                            "ipv4": "192.168.1.100",
                            "ipv6": "2001:db8::1",
                        },
                    },
                },
                "custom": {
                    "description": "Custom metadata specific to your application or use case",
                    "example": {
                        "user_preferences": {"theme": "dark", "notifications": True},
                        "app_settings": {"data_collection": True, "analytics": False},
                        "deployment_info": {
                            "environment": "production",
                            "version": "1.2.3",
                        },
                    },
                },
            },
            "topic": settings.topic_device_metadata,
            "max_size": "1MB",
        },
    )
