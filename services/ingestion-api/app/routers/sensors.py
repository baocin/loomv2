"""REST endpoints for sensor data ingestion."""

import structlog
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from ..kafka_producer import kafka_producer
from ..models import (
    AccelerometerReading,
    GPSReading,
    HeartRateReading,
    PowerState,
    SensorReading,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensors"])


@router.post("/gps", status_code=status.HTTP_201_CREATED)
async def ingest_gps_data(gps_reading: GPSReading) -> JSONResponse:
    """Ingest GPS coordinate data.

    Args:
    ----
        gps_reading: GPS reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_sensor_data(gps_reading, "gps")

        logger.info(
            "GPS data ingested",
            device_id=gps_reading.device_id,
            message_id=gps_reading.message_id,
            latitude=gps_reading.latitude,
            longitude=gps_reading.longitude,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": gps_reading.message_id,
                "topic": "device.sensor.gps.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest GPS data",
            device_id=gps_reading.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest GPS data",
        )


@router.post("/accelerometer", status_code=status.HTTP_201_CREATED)
async def ingest_accelerometer_data(
    accel_reading: AccelerometerReading,
) -> JSONResponse:
    """Ingest accelerometer sensor data.

    Args:
    ----
        accel_reading: Accelerometer reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_sensor_data(accel_reading, "accelerometer")

        logger.info(
            "Accelerometer data ingested",
            device_id=accel_reading.device_id,
            message_id=accel_reading.message_id,
            x=accel_reading.x,
            y=accel_reading.y,
            z=accel_reading.z,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": accel_reading.message_id,
                "topic": "device.sensor.accelerometer.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest accelerometer data",
            device_id=accel_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest accelerometer data",
        ) from e


@router.post("/heartrate", status_code=status.HTTP_201_CREATED)
async def ingest_heartrate_data(hr_reading: HeartRateReading) -> JSONResponse:
    """Ingest heart rate sensor data.

    Args:
    ----
        hr_reading: Heart rate reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_sensor_data(hr_reading, "heartrate")

        logger.info(
            "Heart rate data ingested",
            device_id=hr_reading.device_id,
            message_id=hr_reading.message_id,
            bpm=hr_reading.bpm,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": hr_reading.message_id,
                "topic": "device.health.heartrate.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest heart rate data",
            device_id=hr_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest heart rate data",
        ) from e


@router.post("/power", status_code=status.HTTP_201_CREATED)
async def ingest_power_state(power_state: PowerState) -> JSONResponse:
    """Ingest device power state data.

    Args:
    ----
        power_state: Power state data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_sensor_data(power_state, "power")

        logger.info(
            "Power state data ingested",
            device_id=power_state.device_id,
            message_id=power_state.message_id,
            battery_level=power_state.battery_level,
            is_charging=power_state.is_charging,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": power_state.message_id,
                "topic": "device.state.power.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest power state data",
            device_id=power_state.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest power state data",
        ) from e


@router.post("/generic", status_code=status.HTTP_201_CREATED)
async def ingest_generic_sensor(sensor_reading: SensorReading) -> JSONResponse:
    """Ingest generic sensor data.

    Args:
    ----
        sensor_reading: Generic sensor reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_sensor_data(
            sensor_reading,
            sensor_reading.sensor_type,
        )

        logger.info(
            "Generic sensor data ingested",
            device_id=sensor_reading.device_id,
            message_id=sensor_reading.message_id,
            sensor_type=sensor_reading.sensor_type,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": sensor_reading.message_id,
                "topic": f"device.sensor.{sensor_reading.sensor_type}.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest generic sensor data",
            device_id=sensor_reading.device_id,
            sensor_type=sensor_reading.sensor_type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest sensor data",
        ) from e


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def ingest_sensor_batch(sensor_readings: list[SensorReading]) -> JSONResponse:
    """Ingest a batch of sensor readings.

    Args:
    ----
        sensor_readings: List of sensor readings

    Returns:
    -------
        Success response with processed count

    """
    if not sensor_readings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty batch not allowed",
        )

    try:
        processed_count = 0
        failed_count = 0

        for reading in sensor_readings:
            try:
                await kafka_producer.send_sensor_data(reading, reading.sensor_type)
                processed_count += 1
            except Exception as e:
                logger.error(
                    "Failed to process sensor reading in batch",
                    device_id=reading.device_id,
                    sensor_type=reading.sensor_type,
                    error=str(e),
                )
                failed_count += 1

        logger.info(
            "Sensor batch processed",
            total=len(sensor_readings),
            processed=processed_count,
            failed=failed_count,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "total": len(sensor_readings),
                "processed": processed_count,
                "failed": failed_count,
            },
        )

    except Exception as e:
        logger.error("Failed to process sensor batch", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process sensor batch",
        ) from e
