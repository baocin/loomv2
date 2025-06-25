"""Dead Letter Queue handler for failed message processing."""

import json
import time
from datetime import UTC, datetime
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

logger = structlog.get_logger(__name__)


class DLQHandler:
    """Handles sending failed messages to Dead Letter Queue topics."""

    def __init__(self, producer: AIOKafkaProducer, service_name: str):
        """Initialize DLQ handler.

        Args:
            producer: Kafka producer instance
            service_name: Name of the service using this handler
        """
        self.producer = producer
        self.service_name = service_name

    async def send_to_dlq(
        self,
        original_message: Any,
        source_topic: str,
        error: Exception,
        dlq_topic: str,
        retry_count: int = 0,
        max_retries: int = 3,
    ) -> bool:
        """Send a failed message to the appropriate DLQ topic.

        Args:
            original_message: The original message that failed processing
            source_topic: The topic the message came from
            error: The exception that occurred during processing
            dlq_topic: The DLQ topic to send the message to
            retry_count: Current retry count for this message
            max_retries: Maximum number of retries allowed

        Returns:
            True if successfully sent to DLQ, False otherwise
        """
        try:
            # Create DLQ message with metadata
            dlq_message = {
                "original_message": original_message,
                "error_metadata": {
                    "service": self.service_name,
                    "source_topic": source_topic,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "retry_count": retry_count,
                    "max_retries": max_retries,
                    "failed_at": datetime.now(UTC).isoformat(),
                    "processing_timeout": retry_count >= max_retries,
                },
                "schema_version": "v1",
            }

            # Send to DLQ topic
            await self.producer.send_and_wait(
                dlq_topic,
                value=json.dumps(dlq_message).encode("utf-8"),
                key=self._extract_key(original_message),
            )

            logger.warning(
                "Message sent to DLQ",
                service=self.service_name,
                source_topic=source_topic,
                dlq_topic=dlq_topic,
                error_type=type(error).__name__,
                retry_count=retry_count,
                max_retries=max_retries,
            )

            return True

        except Exception as dlq_error:
            logger.error(
                "Failed to send message to DLQ",
                service=self.service_name,
                dlq_topic=dlq_topic,
                dlq_error=str(dlq_error),
                original_error=str(error),
            )
            return False

    def _extract_key(self, message: Any) -> bytes | None:
        """Extract a key from the original message for partitioning.

        Args:
            message: The original message

        Returns:
            Key as bytes or None
        """
        try:
            # Try to extract device_id as the key
            if isinstance(message, dict):
                device_id = message.get("device_id")
                if device_id:
                    return device_id.encode("utf-8")
            elif hasattr(message, "device_id"):
                return message.device_id.encode("utf-8")

            return None

        except Exception:
            return None

    async def should_retry(
        self, error: Exception, retry_count: int, max_retries: int = 3
    ) -> bool:
        """Determine if a failed message should be retried.

        Args:
            error: The exception that occurred
            retry_count: Current retry count
            max_retries: Maximum retries allowed

        Returns:
            True if should retry, False if should send to DLQ
        """
        # Don't retry if we've exceeded max retries
        if retry_count >= max_retries:
            return False

        # Determine retry eligibility based on error type
        retryable_errors = [
            "ConnectionError",
            "TimeoutError",
            "TemporaryFailure",
            "ModelLoadingError",
            "OutOfMemoryError",
        ]

        error_name = type(error).__name__

        # Always retry network/temporary errors
        if error_name in retryable_errors:
            return True

        # Don't retry validation or permanent errors
        permanent_errors = [
            "ValidationError",
            "ValueError",
            "DecodingError",
            "UnsupportedFormatError",
        ]

        if error_name in permanent_errors:
            return False

        # Default to retry for unknown errors (up to max_retries)
        return True

    def get_retry_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay for retries.

        Args:
            retry_count: Current retry attempt (0-based)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: 2^retry_count seconds, max 60 seconds
        delay = min(2**retry_count, 60)

        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (hash(time.time()) % 10) / 10

        return delay + jitter
