"""Loom API client for sending data to the ingestion service."""

from datetime import datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class LoomAPIClient:
    """HTTP client for the Loom ingestion API."""

    def __init__(self, base_url: str, device_id: str):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.client: httpx.AsyncClient | None = None
        self._healthy = False

    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={"X-API-Key": "apikeyhere"},  # Add API key authentication
        )

        # Test connectivity
        await self.health_check()
        logger.info("Loom API client initialized", base_url=self.base_url)

    async def cleanup(self) -> None:
        """Cleanup the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info("Loom API client cleaned up")

    async def health_check(self) -> bool:
        """Check if the Loom API is healthy."""
        try:
            if not self.client:
                return False

            response = await self.client.get(f"{self.base_url}/healthz")
            self._healthy = response.status_code == 200

            if self._healthy:
                logger.debug("Loom API health check passed")
            else:
                logger.warning(
                    "Loom API health check failed", status_code=response.status_code
                )

            return self._healthy

        except Exception as e:
            logger.error("Loom API health check error", error=str(e))
            self._healthy = False
            return False

    async def send_audio(self, audio_data: bytes, metadata: dict[str, Any]) -> bool:
        """Send audio data to the ingestion API."""
        try:
            import base64

            payload = {
                "device_id": self.device_id,
                "recorded_at": datetime.utcnow().isoformat(),
                "metadata": metadata,
                "sample_rate": metadata.get("sample_rate", 44100),
                "channels": metadata.get("channels", 1),
                "duration_ms": metadata.get("duration_ms", 0),
                "format": metadata.get("format", "wav"),
                "chunk_data": base64.b64encode(audio_data).decode(
                    "utf-8"
                ),  # Use base64 encoding
                "message_id": f"{self.device_id}-{datetime.utcnow().timestamp()}",
            }

            response = await self.client.post(
                f"{self.base_url}/audio/upload", json=payload
            )

            if response.status_code in (200, 201):
                logger.info(
                    "Audio data sent successfully",
                    duration_ms=metadata.get("duration_ms"),
                )
                return True
            else:
                logger.error(
                    "Failed to send audio data",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

        except Exception as e:
            logger.error("Error sending audio data", error=str(e))
            return False

    async def send_sensor_data(self, sensor_type: str, data: dict[str, Any]) -> bool:
        """Send sensor data to the ingestion API."""
        try:
            payload = {
                "device_id": self.device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "schema_version": "v1",
                "message_id": f"{self.device_id}-{datetime.utcnow().timestamp()}",
                **data,
            }

            endpoint_map = {
                "gps": "/sensor/gps",
                "accelerometer": "/sensor/accelerometer",
                "heartrate": "/sensor/heartrate",
                "power": "/sensor/power",
                "generic": "/sensor/generic",
            }

            endpoint = endpoint_map.get(sensor_type, "/sensor/generic")

            response = await self.client.post(
                f"{self.base_url}{endpoint}", json=payload
            )

            if response.status_code in (200, 201):
                logger.debug("Sensor data sent successfully", sensor_type=sensor_type)
                return True
            else:
                logger.error(
                    "Failed to send sensor data",
                    sensor_type=sensor_type,
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

        except Exception as e:
            logger.error(
                "Error sending sensor data", sensor_type=sensor_type, error=str(e)
            )
            return False

    async def send_batch_sensor_data(self, sensor_readings: list) -> bool:
        """Send multiple sensor readings in a batch."""
        try:
            # Ensure all readings have device_id and proper timestamps
            for reading in sensor_readings:
                reading["device_id"] = self.device_id
                if "timestamp" not in reading:
                    reading["timestamp"] = datetime.utcnow().isoformat()
                if "message_id" not in reading:
                    reading[
                        "message_id"
                    ] = f"{self.device_id}-{datetime.utcnow().timestamp()}"

            # Send the list directly as the payload
            response = await self.client.post(
                f"{self.base_url}/sensor/batch", json=sensor_readings
            )

            if response.status_code in (200, 201):
                logger.info(
                    "Batch sensor data sent successfully", count=len(sensor_readings)
                )
                return True
            else:
                logger.error(
                    "Failed to send batch sensor data",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

        except Exception as e:
            logger.error("Error sending batch sensor data", error=str(e))
            return False

    async def send_system_metrics(self, metrics: dict[str, Any]) -> bool:
        """Send system metrics as power state data (temporary workaround)."""
        # Since generic sensor endpoint doesn't exist, we'll send system metrics
        # as part of power state data which can include additional fields
        return await self.send_sensor_data(
            "power",
            {
                "battery_level": metrics.get("battery_level", 100.0),
                "is_charging": metrics.get("is_charging", False),
                "is_plugged_in": metrics.get("is_plugged_in", True),
                # Additional system metrics can be included in metadata
                "metadata": metrics,
            },
        )

    async def send_app_data(self, app_data: dict[str, Any]) -> bool:
        """Send application monitoring data to the system/apps endpoint."""
        try:
            payload = {
                "device_id": self.device_id,
                "recorded_at": datetime.utcnow().isoformat(),
                "running_applications": app_data.get("running_applications", []),
                "message_id": f"{self.device_id}-{datetime.utcnow().timestamp()}",
                "schema_version": "v1",
            }

            response = await self.client.post(
                f"{self.base_url}/system/apps/macos", json=payload
            )

            if response.status_code == 200 or response.status_code == 201:
                logger.info(
                    "App monitoring data sent successfully",
                    app_count=len(app_data.get("running_applications", [])),
                )
                return True
            else:
                logger.error(
                    "Failed to send app monitoring data",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

        except Exception as e:
            logger.error("Error sending app monitoring data", error=str(e))
            return False

    async def send_location_data(self, location: dict[str, Any]) -> bool:
        """Send GPS location data."""
        return await self.send_sensor_data(
            "gps",
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "altitude": location.get("altitude", 0.0),
                "accuracy": location.get("accuracy", 0.0),
                "heading": location.get("heading", 0.0),
                "speed": location.get("speed", 0.0),
            },
        )

    async def send_clipboard_data(self, clipboard_content: str) -> bool:
        """Send clipboard data to digital endpoint (if available) or skip."""
        # Note: Clipboard monitoring should use a dedicated endpoint
        # For now, we'll skip sending clipboard data since generic endpoint doesn't exist
        logger.info(
            "Clipboard data collection skipped - no suitable endpoint",
            content_length=len(clipboard_content),
        )
        return True  # Return True to avoid error counting

    async def send_screen_capture(
        self, image_data: bytes, metadata: dict[str, Any]
    ) -> bool:
        """Send screen capture data to the screenshot endpoint."""
        try:
            import base64

            payload = {
                "device_id": self.device_id,
                "recorded_at": datetime.utcnow().isoformat(),
                "message_id": f"{self.device_id}-{datetime.utcnow().timestamp()}",
                "image_data": base64.b64encode(image_data).decode("utf-8"),
                "format": metadata.get("format", "png"),
                "width": metadata.get("width", 0),
                "height": metadata.get("height", 0),
                "camera_type": "screen",
                "file_size": len(image_data),
                "metadata": metadata,
                "schema_version": "v1",
            }

            response = await self.client.post(
                f"{self.base_url}/images/screenshot", json=payload
            )

            if response.status_code == 200 or response.status_code == 201:
                logger.info(
                    "Screenshot sent successfully",
                    size_bytes=len(image_data),
                    dimensions=f"{metadata.get('width')}x{metadata.get('height')}",
                )
                return True
            else:
                logger.error(
                    "Failed to send screenshot",
                    status_code=response.status_code,
                    response=response.text,
                )
                return False

        except Exception as e:
            logger.error("Error sending screenshot", error=str(e))
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get client status."""
        await self.health_check()

        return {
            "connected": self._healthy,
            "base_url": self.base_url,
            "device_id": self.device_id,
            "client_active": self.client is not None,
        }
