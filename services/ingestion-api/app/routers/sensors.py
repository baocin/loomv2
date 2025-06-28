"""REST endpoints for sensor data ingestion."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import (
    AccelerometerReading,
    BarometerReading,
    GPSReading,
    HeartRateReading,
    NetworkBluetoothReading,
    NetworkWiFiReading,
    PowerState,
    SensorReading,
    TemperatureReading,
)
from ..tracing import get_trace_context

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensors"])


@router.post("/gps", status_code=status.HTTP_201_CREATED)
async def ingest_gps_data(
    gps_reading: GPSReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest GPS coordinate data.

    Args:
    ----
        gps_reading: GPS reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        gps_reading.trace_id = trace_context.get("trace_id")
        gps_reading.services_encountered = trace_context.get("services_encountered", [])

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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
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
    request: Request,
    api_key: str = Depends(verify_api_key),
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
        # Get trace context and add to message
        trace_context = get_trace_context()
        accel_reading.trace_id = trace_context.get("trace_id")
        accel_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
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
async def ingest_heartrate_data(
    hr_reading: HeartRateReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest heart rate sensor data.

    Args:
    ----
        hr_reading: Heart rate reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        hr_reading.trace_id = trace_context.get("trace_id")
        hr_reading.services_encountered = trace_context.get("services_encountered", [])

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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
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
async def ingest_power_state(
    power_state: PowerState,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest device power state data.

    Args:
    ----
        power_state: Power state data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        power_state.trace_id = trace_context.get("trace_id")
        power_state.services_encountered = trace_context.get("services_encountered", [])

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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
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


@router.post("/wifi", status_code=status.HTTP_201_CREATED)
async def ingest_wifi_data(
    wifi_reading: NetworkWiFiReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest WiFi network data.

    Args:
    ----
        wifi_reading: WiFi network reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        wifi_reading.trace_id = trace_context.get("trace_id")
        wifi_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_message(
            topic="device.network.wifi.raw",
            key=wifi_reading.device_id,
            message=wifi_reading,
        )

        logger.info(
            "WiFi data ingested",
            device_id=wifi_reading.device_id,
            message_id=wifi_reading.message_id,
            ssid=wifi_reading.ssid,
            connected=wifi_reading.connected,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": wifi_reading.message_id,
                "topic": "device.network.wifi.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest WiFi data",
            device_id=wifi_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest WiFi data",
        ) from e


@router.post("/bluetooth", status_code=status.HTTP_201_CREATED)
async def ingest_bluetooth_data(
    bt_reading: NetworkBluetoothReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest Bluetooth device data.

    Args:
    ----
        bt_reading: Bluetooth device reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        bt_reading.trace_id = trace_context.get("trace_id")
        bt_reading.services_encountered = trace_context.get("services_encountered", [])

        await kafka_producer.send_message(
            topic="device.network.bluetooth.raw",
            key=bt_reading.device_id,
            message=bt_reading,
        )

        logger.info(
            "Bluetooth data ingested",
            device_id=bt_reading.device_id,
            message_id=bt_reading.message_id,
            device_name=bt_reading.device_name,
            connected=bt_reading.connected,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": bt_reading.message_id,
                "topic": "device.network.bluetooth.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest Bluetooth data",
            device_id=bt_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest Bluetooth data",
        ) from e


@router.post("/temperature", status_code=status.HTTP_201_CREATED)
async def ingest_temperature_data(
    temp_reading: TemperatureReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest temperature sensor data.

    Args:
    ----
        temp_reading: Temperature sensor reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        temp_reading.trace_id = trace_context.get("trace_id")
        temp_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_message(
            topic="device.sensor.temperature.raw",
            key=temp_reading.device_id,
            message=temp_reading,
        )

        logger.info(
            "Temperature data ingested",
            device_id=temp_reading.device_id,
            message_id=temp_reading.message_id,
            temperature=temp_reading.temperature,
            unit=temp_reading.unit,
            location=temp_reading.sensor_location,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": temp_reading.message_id,
                "topic": "device.sensor.temperature.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest temperature data",
            device_id=temp_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest temperature data",
        ) from e


@router.post("/barometer", status_code=status.HTTP_201_CREATED)
async def ingest_barometer_data(
    baro_reading: BarometerReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest barometric pressure data.

    Args:
    ----
        baro_reading: Barometer reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        baro_reading.trace_id = trace_context.get("trace_id")
        baro_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

        await kafka_producer.send_message(
            topic="device.sensor.barometer.raw",
            key=baro_reading.device_id,
            message=baro_reading,
        )

        logger.info(
            "Barometer data ingested",
            device_id=baro_reading.device_id,
            message_id=baro_reading.message_id,
            pressure=baro_reading.pressure,
            unit=baro_reading.unit,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": baro_reading.message_id,
                "topic": "device.sensor.barometer.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest barometer data",
            device_id=baro_reading.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest barometer data",
        ) from e


@router.post("/generic", status_code=status.HTTP_201_CREATED)
async def ingest_generic_sensor(
    sensor_reading: SensorReading,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest generic sensor data.

    Args:
    ----
        sensor_reading: Generic sensor reading data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        sensor_reading.trace_id = trace_context.get("trace_id")
        sensor_reading.services_encountered = trace_context.get(
            "services_encountered",
            [],
        )

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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
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
async def ingest_sensor_batch(
    sensor_readings: list[SensorReading],
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
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
        # Get trace context and add to each message
        trace_context = get_trace_context()

        processed_count = 0
        failed_count = 0

        for reading in sensor_readings:
            try:
                reading.trace_id = trace_context.get("trace_id")
                reading.services_encountered = trace_context.get(
                    "services_encountered",
                    [],
                )
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
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error("Failed to process sensor batch", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process sensor batch",
        ) from e
