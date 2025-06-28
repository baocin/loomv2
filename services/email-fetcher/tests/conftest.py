"""Common test fixtures for email-fetcher tests."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import os


@pytest.fixture
def mock_email_fetcher():
    """Mock EmailFetcher class."""
    with patch('app.main.EmailFetcher') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Mock fetch_all_emails to return sample emails
        mock_instance.fetch_all_emails.return_value = [
            {
                "email_id": "test-email-1",
                "subject": "Test Email 1",
                "sender": "sender1@example.com",
                "recipients": ["recipient@example.com"],
                "body_preview": "This is a test email...",
                "has_attachments": False,
                "date_received": datetime.now(timezone.utc),
                "folder": "INBOX",
                "account_name": "test-account"
            },
            {
                "email_id": "test-email-2",
                "subject": "Test Email 2 with Attachment",
                "sender": "sender2@example.com",
                "recipients": ["recipient@example.com", "cc@example.com"],
                "body_preview": "This email has an attachment...",
                "has_attachments": True,
                "date_received": datetime.now(timezone.utc),
                "folder": "INBOX",
                "account_name": "test-account"
            }
        ]
        
        yield mock_instance


@pytest.fixture
def mock_kafka_producer():
    """Mock KafkaProducer class."""
    with patch('app.main.KafkaProducer') as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        
        # Mock methods
        mock_instance.send_message = MagicMock()
        mock_instance.close = MagicMock()
        
        yield mock_instance


@pytest.fixture
def mock_schedule():
    """Mock schedule module."""
    with patch('app.main.schedule') as mock:
        mock.every = MagicMock()
        mock.run_pending = MagicMock()
        yield mock


@pytest.fixture
def sample_email_data():
    """Sample email data structure."""
    return {
        "email_id": "sample-email-123",
        "subject": "Important: Project Update",
        "sender": "boss@company.com",
        "recipients": ["team@company.com"],
        "body_preview": "Here's the latest update on our project...",
        "has_attachments": True,
        "date_received": datetime(2025, 6, 26, 12, 0, 0, tzinfo=timezone.utc),
        "folder": "INBOX",
        "account_name": "work-email",
        "attachment_names": ["project_plan.pdf", "budget.xlsx"]
    }


@pytest.fixture
def sample_kafka_message():
    """Sample Kafka message structure for email."""
    return {
        "schema_version": "v1",
        "device_id": None,
        "timestamp": "2025-06-26T12:00:00+00:00",
        "data": {
            "email_id": "sample-email-123",
            "subject": "Important: Project Update",
            "sender": "boss@company.com",
            "recipients": ["team@company.com"],
            "body_preview": "Here's the latest update on our project...",
            "has_attachments": True,
            "date_received": "2025-06-26T12:00:00+00:00",
            "folder": "INBOX",
            "account_name": "work-email"
        }
    }


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up test environment variables."""
    test_env = {
        "LOOM_LOG_LEVEL": "INFO",
        "LOOM_KAFKA_OUTPUT_TOPIC": "external.email.events.raw",
        "LOOM_EMAIL_FETCH_INTERVAL_MINUTES": "5",
        "LOOM_EMAIL_RUN_ON_STARTUP": "true"
    }
    
    # Save original environment
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value