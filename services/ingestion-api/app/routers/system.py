"""System monitoring endpoints for app monitoring and device metadata."""

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..api.deps import get_db
from ..auth import verify_api_key
from ..config import settings
from ..kafka_producer import kafka_producer
from ..models import (
    AndroidAppMonitoring,
    AndroidAppUsageAggregated,
    APIResponse,
    DeviceMetadata,
    MacOSAppMonitoring,
)
from ..models.consumer_activity import (
    ConsumerActivityMonitoring,
    ConsumerActivityRequest,
    ConsumerActivityResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.post(
    "/apps/macos",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_macos_app_monitoring(
    app_data: MacOSAppMonitoring,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
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

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_system_apps_macos,
            key=app_data.device_id,
            message=app_data,
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
async def upload_android_app_monitoring(
    app_data: AndroidAppMonitoring,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
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

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_system_apps_android,
            key=app_data.device_id,
            message=app_data,
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


@router.post(
    "/apps/android/usage",
    status_code=status.HTTP_201_CREATED,
    response_model=APIResponse,
)
async def upload_android_usage_stats(
    usage_data: AndroidAppUsageAggregated,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Upload pre-aggregated Android app usage statistics.

    This endpoint accepts pre-aggregated usage statistics from Android's UsageStats API,
    including app usage times, screen time by category, notification stats, and app events.

    Args:
    ----
        usage_data: Pre-aggregated Android app usage statistics

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
        # Send to Kafka
        await kafka_producer.send_message(
            topic="device.app_usage.android.aggregated",
            key=usage_data.device_id,
            message=usage_data,
        )

        logger.info(
            "Android usage stats sent to Kafka",
            device_id=usage_data.device_id,
            message_id=usage_data.message_id,
            aggregation_start=usage_data.aggregation_period_start,
            aggregation_end=usage_data.aggregation_period_end,
            total_screen_time_ms=usage_data.total_screen_time_ms,
            app_count=len(usage_data.app_usage_stats),
            topic="device.app_usage.android.aggregated",
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": usage_data.message_id,
                "topic": "device.app_usage.android.aggregated",
                "aggregation_period": {
                    "start": usage_data.aggregation_period_start.isoformat(),
                    "end": usage_data.aggregation_period_end.isoformat(),
                },
                "stats": {
                    "total_screen_time_ms": usage_data.total_screen_time_ms,
                    "app_count": len(usage_data.app_usage_stats),
                    "event_count": len(usage_data.app_event_stats),
                },
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to process Android usage stats",
            device_id=usage_data.device_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Android usage stats: {e!s}",
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
async def upload_device_metadata(
    metadata: DeviceMetadata,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
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

        # Send to Kafka
        await kafka_producer.send_message(
            topic=settings.topic_device_metadata,
            key=metadata.device_id,
            message=metadata,
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


# Consumer Activity Monitoring Endpoints


@router.post(
    "/consumer_activity/log",
    response_model=ConsumerActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Log consumer activity",
    description="Log the last consumed and/or produced message for a Kafka consumer",
)
async def log_consumer_activity(
    request: ConsumerActivityRequest,
    db=Depends(get_db),
) -> JSONResponse:
    """Log consumer activity to the database.

    Args:
    ----
        request: Consumer activity data including consumer_id and optional message info

    Returns:
    -------
        ConsumerActivityResponse with the logged data

    """
    try:
        # Use the database function for atomic upsert
        query = text(
            """
            SELECT * FROM upsert_consumer_activity(
                p_consumer_id := :consumer_id,
                p_consumed_message := :consumed_message,
                p_produced_message := :produced_message,
                p_consumed_at := :consumed_at,
                p_produced_at := :produced_at
            )
        """,
        )

        result = await db.fetch_one(
            query=query,
            values={
                "consumer_id": request.consumer_id,
                "consumed_message": (
                    json.dumps(request.consumed_message)
                    if request.consumed_message
                    else None
                ),
                "produced_message": (
                    json.dumps(request.produced_message)
                    if request.produced_message
                    else None
                ),
                "consumed_at": request.consumed_at,
                "produced_at": request.produced_at,
            },
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log consumer activity",
            )

        # Convert result to response model
        response = ConsumerActivityResponse(
            id=result["id"],
            consumer_id=result["consumer_id"],
            last_consumed_message=(
                json.loads(result["last_consumed_message"])
                if result["last_consumed_message"]
                else None
            ),
            last_produced_message=(
                json.loads(result["last_produced_message"])
                if result["last_produced_message"]
                else None
            ),
            message_consumed_at=result["message_consumed_at"],
            message_produced_at=result["message_produced_at"],
            last_complete_processed_consumed_message=(
                json.loads(result["last_complete_processed_consumed_message"])
                if result["last_complete_processed_consumed_message"]
                else None
            ),
            last_complete_processed_produced_message=(
                json.loads(result["last_complete_processed_produced_message"])
                if result["last_complete_processed_produced_message"]
                else None
            ),
            created_at=result["created_at"],
            updated_at=result["updated_at"],
        )

        logger.info(
            "Consumer activity logged",
            consumer_id=request.consumer_id,
            has_consumed=bool(request.consumed_message),
            has_produced=bool(request.produced_message),
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(mode="json"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to log consumer activity",
            consumer_id=request.consumer_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log consumer activity: {e!s}",
        )


@router.get(
    "/consumer_activity",
    response_model=list[ConsumerActivityMonitoring],
    status_code=status.HTTP_200_OK,
    summary="Get consumer activity monitoring data",
    description="Retrieve current consumer activity and health status",
)
async def get_consumer_activity_monitoring(
    db=Depends(get_db),
) -> list[ConsumerActivityMonitoring]:
    """Get consumer activity monitoring data.

    Returns a list of all consumers with their current processing status,
    including:
    - Last consumed/produced timestamps
    - Processing time metrics
    - Health status (inactive, stuck, etc.)
    """
    try:
        query = text(
            """
            SELECT * FROM consumer_activity_monitoring
            ORDER BY
                health_status = 'inactive' DESC,
                health_status = 'stuck' DESC,
                last_update_minutes_ago DESC
        """,
        )

        rows = await db.fetch_all(query=query)

        return [
            ConsumerActivityMonitoring(
                consumer_id=row["consumer_id"],
                last_consumed_at=row["last_consumed_at"],
                last_produced_at=row["last_produced_at"],
                last_update_minutes_ago=row["last_update_minutes_ago"],
                consumed_to_produced_seconds=row["consumed_to_produced_seconds"],
                health_status=row["health_status"],
                is_active_consumer=row["is_active_consumer"],
                is_active_producer=row["is_active_producer"],
            )
            for row in rows
        ]

    except Exception as e:
        logger.error(
            "Failed to get consumer activity monitoring",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get consumer activity: {e!s}",
        )
