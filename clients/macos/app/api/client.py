"""Loom API client for sending data to the ingestion service."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
import structlog

logger = structlog.get_logger(__name__)


class LoomAPIClient:
    """HTTP client for the Loom ingestion API."""
    
    def __init__(self, base_url: str, device_id: str):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.client: Optional[httpx.AsyncClient] = None
        self._healthy = False
    
    async def initialize(self) -> None:
        """Initialize the HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
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
                logger.warning("Loom API health check failed", 
                             status_code=response.status_code)
            
            return self._healthy
            
        except Exception as e:
            logger.error("Loom API health check error", error=str(e))
            self._healthy = False
            return False
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """Send audio data to the ingestion API."""
        try:
            payload = {
                "device_id": self.device_id,
                "recorded_at": datetime.utcnow().isoformat(),
                "metadata": metadata,
                "sample_rate": metadata.get("sample_rate", 44100),
                "channels": metadata.get("channels", 1),
                "duration_ms": metadata.get("duration_ms", 0),
                "format": metadata.get("format", "wav"),
                "audio_data": audio_data.hex()  # Convert to hex string
            }
            
            response = await self.client.post(
                f"{self.base_url}/audio/upload",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info("Audio data sent successfully", 
                           duration_ms=metadata.get("duration_ms"))
                return True
            else:
                logger.error("Failed to send audio data", 
                           status_code=response.status_code,
                           response=response.text)
                return False
                
        except Exception as e:
            logger.error("Error sending audio data", error=str(e))
            return False
    
    async def send_sensor_data(self, sensor_type: str, data: Dict[str, Any]) -> bool:
        """Send sensor data to the ingestion API."""
        try:
            payload = {
                "device_id": self.device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "schema_version": "v1",
                "message_id": f"{self.device_id}-{datetime.utcnow().timestamp()}",
                **data
            }
            
            endpoint_map = {
                "gps": "/sensor/gps",
                "accelerometer": "/sensor/accelerometer", 
                "heartrate": "/sensor/heartrate",
                "power": "/sensor/power",
                "generic": "/sensor/generic"
            }
            
            endpoint = endpoint_map.get(sensor_type, "/sensor/generic")
            
            response = await self.client.post(
                f"{self.base_url}{endpoint}",
                json=payload
            )
            
            if response.status_code == 200:
                logger.debug("Sensor data sent successfully", 
                           sensor_type=sensor_type)
                return True
            else:
                logger.error("Failed to send sensor data",
                           sensor_type=sensor_type,
                           status_code=response.status_code,
                           response=response.text)
                return False
                
        except Exception as e:
            logger.error("Error sending sensor data", 
                        sensor_type=sensor_type, error=str(e))
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
                    reading["message_id"] = f"{self.device_id}-{datetime.utcnow().timestamp()}"
            
            payload = {
                "device_id": self.device_id,
                "readings": sensor_readings
            }
            
            response = await self.client.post(
                f"{self.base_url}/sensor/batch",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info("Batch sensor data sent successfully", 
                           count=len(sensor_readings))
                return True
            else:
                logger.error("Failed to send batch sensor data",
                           status_code=response.status_code,
                           response=response.text)
                return False
                
        except Exception as e:
            logger.error("Error sending batch sensor data", error=str(e))
            return False
    
    async def send_system_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Send system metrics as generic sensor data."""
        return await self.send_sensor_data("generic", {
            "sensor_type": "system_metrics",
            "value": 0,  # Required field, but we use readings for actual data
            "unit": "mixed",
            "readings": metrics
        })
    
    async def send_app_data(self, app_data: Dict[str, Any]) -> bool:
        """Send application monitoring data as generic sensor data."""
        return await self.send_sensor_data("generic", {
            "sensor_type": "app_monitoring",
            "value": app_data.get("active_app_count", 0),
            "unit": "count",
            "readings": app_data
        })
    
    async def send_location_data(self, location: Dict[str, Any]) -> bool:
        """Send GPS location data."""
        return await self.send_sensor_data("gps", {
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "altitude": location.get("altitude", 0.0),
            "accuracy": location.get("accuracy", 0.0),
            "heading": location.get("heading", 0.0),
            "speed": location.get("speed", 0.0)
        })
    
    async def send_clipboard_data(self, clipboard_content: str) -> bool:
        """Send clipboard data as generic sensor data."""
        return await self.send_sensor_data("generic", {
            "sensor_type": "clipboard",
            "value": len(clipboard_content),
            "unit": "characters",
            "readings": {
                "content_length": len(clipboard_content),
                "content_hash": hash(clipboard_content),  # Don't send actual content for privacy
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    async def send_screen_capture(self, image_data: bytes, metadata: Dict[str, Any]) -> bool:
        """Send screen capture data (placeholder - would need actual endpoint)."""
        # Note: This would require a dedicated endpoint for image data
        # For now, we'll send metadata only
        return await self.send_sensor_data("generic", {
            "sensor_type": "screen_capture",
            "value": len(image_data),
            "unit": "bytes", 
            "readings": {
                "image_size_bytes": len(image_data),
                "width": metadata.get("width", 0),
                "height": metadata.get("height", 0),
                "format": metadata.get("format", "png"),
                "timestamp": datetime.utcnow().isoformat()
            }
        })
    
    async def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        await self.health_check()
        
        return {
            "connected": self._healthy,
            "base_url": self.base_url,
            "device_id": self.device_id,
            "client_active": self.client is not None
        }