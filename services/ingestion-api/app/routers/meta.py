"""Meta endpoints for system monitoring and activity logging."""


import structlog
from asyncpg import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.deps import get_db
from app.schemas.consumer_activity import (
    ConsumerActivityMonitoring,
    ConsumerActivityRequest,
    ConsumerActivityResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post(
    "/log_activity",
    response_model=ConsumerActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Log consumer activity",
    description="Log the last consumed and/or produced message for a Kafka consumer",
)
async def log_consumer_activity(
    request: ConsumerActivityRequest,
    db=Depends(get_db),
) -> ConsumerActivityResponse:
    """Log consumer activity including consumed and produced messages.

    This endpoint is called by Kafka consumers to track their processing activity:
    - When a message is consumed: Send consumed_message and consumed_at
    - When a message is produced: Send produced_message and produced_at

    The endpoint uses upsert logic to handle concurrent updates safely.
    """
    try:
        # Call the database function to upsert consumer activity
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
            query,
            values={
                "consumer_id": request.consumer_id,
                "consumed_message": request.consumed_message,
                "produced_message": request.produced_message,
                "consumed_at": request.consumed_at,
                "produced_at": request.produced_at,
            },
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to log consumer activity",
            )

        logger.info(
            "Consumer activity logged",
            consumer_id=request.consumer_id,
            has_consumed=request.consumed_message is not None,
            has_produced=request.produced_message is not None,
        )

        return ConsumerActivityResponse(
            success=True,
            message="Consumer activity logged successfully",
            data=result,
        )

    except UniqueViolationError as e:
        logger.error(
            "Unique constraint violation",
            consumer_id=request.consumer_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Consumer ID conflict: {request.consumer_id}",
        )
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
            SELECT * FROM v_consumer_activity_monitoring
            ORDER BY is_stuck DESC, is_inactive DESC, seconds_since_consumed DESC
            """,
        )

        results = await db.fetch_all(query)

        return [ConsumerActivityMonitoring(**dict(row)) for row in results]

    except Exception as e:
        logger.error(
            "Failed to fetch consumer activity monitoring",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch consumer activity: {e!s}",
        )


@router.get(
    "/consumer_activity/{consumer_id}",
    response_model=ConsumerActivityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get specific consumer activity",
    description="Retrieve activity details for a specific consumer",
)
async def get_consumer_activity(
    consumer_id: str,
    db=Depends(get_db),
) -> ConsumerActivityResponse:
    """Get activity details for a specific consumer.

    Returns the full activity log entry including last consumed and produced messages.
    """
    try:
        query = text(
            """
            SELECT * FROM logged_consumer_activity
            WHERE consumer_id = :consumer_id
            """,
        )

        result = await db.fetch_one(query, values={"consumer_id": consumer_id})

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Consumer activity not found for: {consumer_id}",
            )

        return ConsumerActivityResponse(
            success=True,
            message="Consumer activity retrieved successfully",
            data=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch consumer activity",
            consumer_id=consumer_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch consumer activity: {e!s}",
        )
