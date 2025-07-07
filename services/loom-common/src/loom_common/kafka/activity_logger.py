"""Activity logging for Kafka consumers."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class ConsumerActivityLogger:
    """Mixin class to add activity logging to Kafka consumers."""

    def __init__(
        self,
        service_name: str,
        ingestion_host: str = "ingestion-api",
        ingestion_port: int = 8000,
    ):
        """Initialize the activity logger.

        Args:
            service_name: Name of the consumer service
            ingestion_host: Host of the ingestion API
            ingestion_port: Port of the ingestion API
        """
        self.service_name = service_name
        self.activity_logging_url = (
            f"http://{ingestion_host}:{ingestion_port}/meta/log_activity"
        )
        self._http_client: Optional[httpx.AsyncClient] = None
        self._activity_logging_enabled = True

    async def init_activity_logger(self) -> None:
        """Initialize the HTTP client for activity logging."""
        if self._activity_logging_enabled and not self._http_client:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)
            )
            logger.info(
                "Activity logging initialized",
                url=self.activity_logging_url,
                service_name=self.service_name,
            )

    async def close_activity_logger(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def log_consumption(self, message: Any) -> None:
        """Log that a message was consumed.

        Args:
            message: The consumed message (should have a .value attribute)
        """
        if not self._activity_logging_enabled or not self._http_client:
            return

        try:
            # Extract message value - handle both dict and ConsumerRecord
            message_value = message.value if hasattr(message, "value") else message

            payload = {
                "consumer_id": self.service_name,
                "consumed_message": message_value,
                "consumed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Fire and forget - don't await to avoid blocking
            asyncio.create_task(self._send_activity_log(payload))

        except Exception as e:
            logger.debug(
                "Error preparing consumption log",
                error=str(e),
                service_name=self.service_name,
            )

    async def log_production(
        self, topic: str, value: Dict[str, Any], key: Optional[str] = None
    ) -> None:
        """Log that a message was produced.

        Args:
            topic: Topic where the message was sent
            value: The message value
            key: Optional message key
        """
        if not self._activity_logging_enabled or not self._http_client:
            return

        try:
            payload = {
                "consumer_id": self.service_name,
                "produced_message": {
                    "topic": topic,
                    "key": key,
                    "value": value,
                },
                "produced_at": datetime.now(timezone.utc).isoformat(),
            }

            # Fire and forget - don't await to avoid blocking
            asyncio.create_task(self._send_activity_log(payload))

        except Exception as e:
            logger.debug(
                "Error preparing production log",
                error=str(e),
                service_name=self.service_name,
            )

    async def _send_activity_log(self, payload: Dict[str, Any]) -> None:
        """Send activity log to the API.

        Args:
            payload: The log payload
        """
        try:
            response = await self._http_client.post(
                self.activity_logging_url,
                json=payload,
            )

            if response.status_code != 200:
                logger.debug(
                    "Failed to send activity log",
                    status_code=response.status_code,
                    response=response.text[:200],  # Limit response size
                )

        except Exception as e:
            # Don't let logging failures affect message processing
            logger.debug(
                "Error sending activity log",
                error=str(e),
                service_name=self.service_name,
            )
