"""Email consumer for Gmail API integration."""

import os
from datetime import datetime, timedelta
from typing import List

import structlog

from ..config import settings
from ..models import BaseMessage, EmailEvent
from .base_consumer import BaseConsumer

logger = structlog.get_logger(__name__)


class EmailConsumer(BaseConsumer):
    """Consumer for email data from Gmail API."""

    def __init__(self):
        """Initialize email consumer."""
        super().__init__(
            job_type="email_sync",
            interval_minutes=settings.email_check_interval_minutes,
        )
        self._last_sync_time: datetime | None = None

    async def collect_data(self) -> List[BaseMessage]:
        """Collect email data from Gmail API.

        Returns:
        -------
            List of EmailEvent messages
        """
        messages = []

        try:
            # TODO: Implement actual Gmail API integration
            if not settings.gmail_credentials_path or not os.path.exists(
                settings.gmail_credentials_path
            ):
                logger.warning(
                    "Gmail credentials not configured, returning empty list",
                    credentials_path=settings.gmail_credentials_path,
                )
                return []

            # TODO: Implement Gmail API client
            # from google.oauth2.credentials import Credentials
            # from googleapiclient.discovery import build

            logger.info("Collecting email data from Gmail API")

            # For now, return empty list until Gmail API is implemented
            return messages

        except Exception as e:
            logger.error("Failed to collect email data", error=str(e))
            raise

    def get_kafka_topic(self) -> str:
        """Get Kafka topic for email events."""
        return "external.email.events.raw"

    async def _get_mock_email_data(self) -> List[BaseMessage]:
        """Generate mock email data for testing."""
        mock_emails = []

        # Generate 2-5 mock emails
        import random

        num_emails = random.randint(2, 5)

        for i in range(num_emails):
            email = EmailEvent(
                device_id=settings.device_id,
                message_id_external=f"mock_email_{i}_{datetime.utcnow().timestamp()}",
                from_address=f"sender{i}@example.com",
                to_addresses=[f"user@{settings.device_id}.com"],
                subject=f"Mock Email {i} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                body_text=f"This is mock email content {i} for testing purposes.",
                is_read=random.choice([True, False]),
                is_starred=random.choice(
                    [True, False, False]
                ),  # Lower chance of starred
                labels=random.choice(
                    [["inbox"], ["inbox", "important"], ["inbox", "work"], ["archive"]]
                ),
                received_date=datetime.utcnow()
                - timedelta(minutes=random.randint(1, 1440)),
            )
            mock_emails.append(email)

        logger.info(f"Generated {len(mock_emails)} mock email events")
        return mock_emails
