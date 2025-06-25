"""API client for communicating with Loom ingestion service."""

import base64
from datetime import UTC, datetime
from typing import Any

import aiohttp
import structlog

logger = structlog.get_logger(__name__)


class LoomAPIClient:
    """Async API client for Loom ingestion service."""

    def __init__(self, base_url: str, device_id: str, timeout: float = 30.0):
        """Initialize the API client.

        Args:
            base_url: Base URL of the Loom API
            device_id: Unique device identifier
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

        logger.info(
            "API client initialized", base_url=self.base_url, device_id=self.device_id
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is created."""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=aiohttp.TCPConnector(limit=100),
                headers={"User-Agent": f"pino-proxy-ubuntu/{self.device_id}"},
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _get_common_payload(self) -> dict[str, Any]:
        """Get common payload fields."""
        return {
            "device_id": self.device_id,
            "recorded_at": datetime.now(UTC).isoformat(),
        }

    async def _make_request(
        self, method: str, endpoint: str, data: dict[str, Any]
    ) -> bool:
        """Make HTTP request to API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request payload

        Returns:
            True if successful, False otherwise
        """
        await self._ensure_session()

        url = f"{self.base_url}{endpoint}"

        try:
            async with self._session.request(method, url, json=data) as response:
                if response.status == 200:
                    logger.debug(
                        "API request successful",
                        endpoint=endpoint,
                        status=response.status,
                    )
                    return True
                else:
                    response_text = await response.text()
                    logger.warning(
                        "API request failed",
                        endpoint=endpoint,
                        status=response.status,
                        response=response_text,
                    )
                    return False

        except TimeoutError:
            logger.error("API request timeout", endpoint=endpoint)
            return False
        except Exception as e:
            logger.error("API request error", endpoint=endpoint, error=str(e))
            return False

    # Audio endpoints
    async def send_audio(self, audio_data: bytes, metadata: dict[str, Any]) -> bool:
        """Send audio data to the ingestion API."""
        try:
            # Encode audio data as base64
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

            payload = {
                **self._get_common_payload(),
                "audio_data": audio_b64,
                "metadata": metadata,
            }

            return await self._make_request("POST", "/audio/upload", payload)

        except Exception as e:
            logger.error("Error sending audio data", error=str(e))
            return False

    # Sensor endpoints
    async def send_sensor_data(self, sensor_type: str, data: dict[str, Any]) -> bool:
        """Send sensor data to the ingestion API."""
        try:
            payload = {**self._get_common_payload(), **data}

            endpoint = f"/sensor/{sensor_type}"
            return await self._make_request("POST", endpoint, payload)

        except Exception as e:
            logger.error(
                "Error sending sensor data", sensor_type=sensor_type, error=str(e)
            )
            return False

    async def send_gps_data(
        self,
        latitude: float,
        longitude: float,
        accuracy: float | None = None,
        **kwargs,
    ) -> bool:
        """Send GPS coordinates."""
        data = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            **kwargs,
        }
        return await self.send_sensor_data("gps", data)

    async def send_accelerometer_data(
        self, x: float, y: float, z: float, **kwargs
    ) -> bool:
        """Send accelerometer data."""
        data = {"x": x, "y": y, "z": z, **kwargs}
        return await self.send_sensor_data("accelerometer", data)

    async def send_heartrate_data(
        self, heartrate: int, confidence: float | None = None, **kwargs
    ) -> bool:
        """Send heart rate data."""
        data = {"heartrate": heartrate, "confidence": confidence, **kwargs}
        return await self.send_sensor_data("heartrate", data)

    async def send_power_data(
        self, battery_level: float, is_charging: bool, **kwargs
    ) -> bool:
        """Send power/battery data."""
        data = {"battery_level": battery_level, "is_charging": is_charging, **kwargs}
        return await self.send_sensor_data("power", data)

    # Screen capture endpoint
    async def send_screen_capture(
        self, image_data: bytes, metadata: dict[str, Any]
    ) -> bool:
        """Send screen capture data."""
        try:
            # Encode image data as base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")

            payload = {
                **self._get_common_payload(),
                "image_data": image_b64,
                "metadata": metadata,
            }

            # Note: This endpoint may need to be created in the Loom API
            return await self._make_request("POST", "/media/screen", payload)

        except Exception as e:
            logger.error("Error sending screen capture", error=str(e))
            return False

    # App monitoring endpoint
    async def send_app_monitoring(
        self, apps_data: dict[str, Any], metadata: dict[str, Any]
    ) -> bool:
        """Send application monitoring data."""
        try:
            payload = {
                **self._get_common_payload(),
                "apps_data": apps_data,
                "metadata": metadata,
            }

            # Note: This endpoint may need to be created in the Loom API
            return await self._make_request("POST", "/system/apps", payload)

        except Exception as e:
            logger.error("Error sending app monitoring data", error=str(e))
            return False

    # Clipboard endpoint
    async def send_clipboard_data(
        self, clipboard_data: dict[str, Any], metadata: dict[str, Any]
    ) -> bool:
        """Send clipboard data."""
        try:
            payload = {
                **self._get_common_payload(),
                "clipboard_data": clipboard_data,
                "metadata": metadata,
            }

            # Note: This endpoint may need to be created in the Loom API
            return await self._make_request("POST", "/system/clipboard", payload)

        except Exception as e:
            logger.error("Error sending clipboard data", error=str(e))
            return False

    # Batch endpoint for multiple sensor readings
    async def send_sensor_batch(self, sensor_readings: list[dict[str, Any]]) -> bool:
        """Send batch of sensor readings."""
        try:
            # Add common payload to each reading
            for reading in sensor_readings:
                if "device_id" not in reading:
                    reading["device_id"] = self.device_id
                if "recorded_at" not in reading:
                    reading["recorded_at"] = datetime.now(UTC).isoformat()

            payload = {"readings": sensor_readings}

            return await self._make_request("POST", "/sensor/batch", payload)

        except Exception as e:
            logger.error("Error sending sensor batch", error=str(e))
            return False

    # Health check
    async def health_check(self) -> bool:
        """Check if the API is healthy."""
        try:
            await self._ensure_session()
            url = f"{self.base_url}/healthz"

            async with self._session.get(url) as response:
                return response.status == 200

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return False

    async def get_api_info(self) -> dict[str, Any] | None:
        """Get API information."""
        try:
            await self._ensure_session()
            url = f"{self.base_url}/"

            async with self._session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None

        except Exception as e:
            logger.error("Failed to get API info", error=str(e))
            return None
