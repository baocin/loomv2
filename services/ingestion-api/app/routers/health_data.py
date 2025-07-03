"""REST endpoints for health data ingestion."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import (
    BloodOxygenReading,
    BloodPressureReading,
    SleepReading,
    StepsReading,
)
from ..tracing import get_trace_context

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/steps", status_code=status.HTTP_201_CREATED)
async def ingest_steps_data(
    steps_reading: StepsReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest step counter data.

    Args:
    ----
        steps_reading: Step counter reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        steps_reading.trace_id = trace_context.get("trace_id")
        steps_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_health_data(steps_reading, "steps")

        logger.info(
            "Steps data ingested",
            device_id=steps_reading.device_id,
            message_id=steps_reading.message_id,
            step_count=steps_reading.step_count,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": steps_reading.message_id,
                "topic": "device.health.steps.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest steps data",
            device_id=steps_reading.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest steps data",
        )


@router.post("/sleep", status_code=status.HTTP_201_CREATED)
async def ingest_sleep_data(
    sleep_reading: SleepReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest sleep tracking data.

    Args:
    ----
        sleep_reading: Sleep tracking data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        sleep_reading.trace_id = trace_context.get("trace_id")
        sleep_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_health_data(sleep_reading, "sleep")

        logger.info(
            "Sleep data ingested",
            device_id=sleep_reading.device_id,
            message_id=sleep_reading.message_id,
            sleep_stage=sleep_reading.sleep_stage,
            duration_seconds=sleep_reading.duration_seconds,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": sleep_reading.message_id,
                "topic": "device.health.sleep.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest sleep data",
            device_id=sleep_reading.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest sleep data",
        )


@router.post("/blood-oxygen", status_code=status.HTTP_201_CREATED)
async def ingest_blood_oxygen_data(
    blood_oxygen_reading: BloodOxygenReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest blood oxygen saturation data.

    Args:
    ----
        blood_oxygen_reading: Blood oxygen reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        blood_oxygen_reading.trace_id = trace_context.get("trace_id")
        blood_oxygen_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_health_data(blood_oxygen_reading, "blood_oxygen")

        logger.info(
            "Blood oxygen data ingested",
            device_id=blood_oxygen_reading.device_id,
            message_id=blood_oxygen_reading.message_id,
            spo2_percentage=blood_oxygen_reading.spo2_percentage,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": blood_oxygen_reading.message_id,
                "topic": "device.health.blood_oxygen.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest blood oxygen data",
            device_id=blood_oxygen_reading.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest blood oxygen data",
        )


@router.post("/blood-pressure", status_code=status.HTTP_201_CREATED)
async def ingest_blood_pressure_data(
    blood_pressure_reading: BloodPressureReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest blood pressure data.

    Args:
    ----
        blood_pressure_reading: Blood pressure reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        blood_pressure_reading.trace_id = trace_context.get("trace_id")
        blood_pressure_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_health_data(blood_pressure_reading, "blood_pressure")

        logger.info(
            "Blood pressure data ingested",
            device_id=blood_pressure_reading.device_id,
            message_id=blood_pressure_reading.message_id,
            systolic=blood_pressure_reading.systolic,
            diastolic=blood_pressure_reading.diastolic,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": blood_pressure_reading.message_id,
                "topic": "device.health.blood_pressure.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest blood pressure data",
            device_id=blood_pressure_reading.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest blood pressure data",
        )
