"""Unit tests for OS events endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import OSEventAppLifecycle, OSEventNotification, OSEventSystemRaw


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.os_events.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        yield mock


def create_os_event_base_data() -> dict:
    """Create base test data for OS events."""
    from ..test_helpers import create_base_test_data

    return create_base_test_data()


def create_app_lifecycle_test_data() -> dict:
    """Create test data for app lifecycle events."""
    base_data = create_os_event_base_data()
    base_data.update(
        {
            "app_identifier": "com.example.testapp",
            "app_name": "Test App",
            "event_type": "launch",
            "duration_seconds": 120,
            "metadata": {
                "version": "1.0.0",
                "build": "123",
                "previous_state": "background",
            },
        },
    )
    return base_data


def create_system_event_test_data() -> dict:
    """Create test data for system events."""
    base_data = create_os_event_base_data()
    base_data.update(
        {
            "event_type": "screen_on",
            "event_category": "screen",
            "severity": "info",
            "description": "Device screen turned on",
            "metadata": {"brightness": 80, "auto_brightness": True},
        },
    )
    return base_data


def create_notification_test_data() -> dict:
    """Create test data for notification events."""
    base_data = create_os_event_base_data()
    base_data.update(
        {
            "notification_id": "notif_12345",
            "app_identifier": "com.example.messenger",
            "title": "New Message",
            "body": "You have a new message from John",
            "action": "posted",
            "metadata": {
                "channel_id": "messages",
                "priority": "high",
                "sound": "default",
            },
        },
    )
    return base_data


class TestAppLifecycleEvents:
    """Test app lifecycle event endpoints."""

    def test_upload_app_lifecycle_event_success(self, client, mock_kafka_producer):
        """Test successful app lifecycle event upload."""
        test_data = create_app_lifecycle_test_data()

        response = client.post("/os-events/app-lifecycle", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "os.events.app_lifecycle.raw"
        assert data["event_type"] == "launch"
        assert data["app_identifier"] == "com.example.testapp"
        assert "message_id" in data

        # Verify Kafka producer was called
        mock_kafka_producer.send_message.assert_called_once()
        call_args = mock_kafka_producer.send_message.call_args
        assert call_args[1]["topic"] == "os.events.app_lifecycle.raw"
        assert call_args[1]["key"] == test_data["device_id"]

    def test_upload_app_lifecycle_event_all_types(self, client, mock_kafka_producer):
        """Test all supported app lifecycle event types."""
        event_types = ["launch", "foreground", "background", "terminate", "crash"]

        for event_type in event_types:
            test_data = create_app_lifecycle_test_data()
            test_data["event_type"] = event_type

            response = client.post("/os-events/app-lifecycle", json=test_data)

            assert response.status_code == 201
            data = response.json()
            assert data["event_type"] == event_type

    def test_upload_app_lifecycle_event_invalid_type(self, client):
        """Test app lifecycle event with invalid event type."""
        test_data = create_app_lifecycle_test_data()
        test_data["event_type"] = "invalid_type"

        response = client.post("/os-events/app-lifecycle", json=test_data)
        assert response.status_code == 422

    def test_upload_app_lifecycle_event_missing_required_fields(self, client):
        """Test app lifecycle event with missing required fields."""
        test_data = create_app_lifecycle_test_data()
        del test_data["app_identifier"]

        response = client.post("/os-events/app-lifecycle", json=test_data)
        assert response.status_code == 422

    def test_upload_app_lifecycle_event_kafka_failure(self, client):
        """Test app lifecycle event when Kafka fails."""
        with patch("app.routers.os_events.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_app_lifecycle_test_data()
            response = client.post("/os-events/app-lifecycle", json=test_data)

            assert response.status_code == 500
            assert "Failed to process app lifecycle event" in response.json()["detail"]


class TestSystemEvents:
    """Test system event endpoints."""

    def test_upload_system_event_success(self, client, mock_kafka_producer):
        """Test successful system event upload."""
        test_data = create_system_event_test_data()

        response = client.post("/os-events/system", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "os.events.system.raw"
        assert data["event_type"] == "screen_on"
        assert data["event_category"] == "screen"
        assert "message_id" in data

    def test_upload_system_event_various_types(self, client, mock_kafka_producer):
        """Test various system event types."""
        event_configs = [
            {"type": "screen_off", "category": "screen"},
            {"type": "device_lock", "category": "lock"},
            {"type": "device_unlock", "category": "lock"},
            {"type": "power_connected", "category": "power"},
            {"type": "power_disconnected", "category": "power"},
            {"type": "boot_completed", "category": "system"},
            {"type": "shutdown", "category": "system"},
        ]

        for config in event_configs:
            test_data = create_system_event_test_data()
            test_data["event_type"] = config["type"]
            test_data["event_category"] = config["category"]

            response = client.post("/os-events/system", json=test_data)

            assert response.status_code == 201
            data = response.json()
            assert data["event_type"] == config["type"]
            assert data["event_category"] == config["category"]

    def test_upload_system_event_minimal_data(self, client, mock_kafka_producer):
        """Test system event with minimal required data."""
        base_data = create_os_event_base_data()
        base_data.update({"event_type": "screen_on"})

        response = client.post("/os-events/system", json=base_data)
        assert response.status_code == 201

    def test_upload_system_event_kafka_failure(self, client):
        """Test system event when Kafka fails."""
        with patch("app.routers.os_events.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_system_event_test_data()
            response = client.post("/os-events/system", json=test_data)

            assert response.status_code == 500
            assert "Failed to process system event" in response.json()["detail"]


class TestNotificationEvents:
    """Test notification event endpoints."""

    def test_upload_notification_event_success(self, client, mock_kafka_producer):
        """Test successful notification event upload."""
        test_data = create_notification_test_data()

        response = client.post("/os-events/notifications", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "os.events.notifications.raw"
        assert data["notification_id"] == "notif_12345"
        assert data["action"] == "posted"
        assert "message_id" in data

    def test_upload_notification_event_all_actions(self, client, mock_kafka_producer):
        """Test all notification actions."""
        actions = ["posted", "removed", "clicked"]

        for action in actions:
            test_data = create_notification_test_data()
            test_data["action"] = action

            response = client.post("/os-events/notifications", json=test_data)

            assert response.status_code == 201
            data = response.json()
            assert data["action"] == action

    def test_upload_notification_event_minimal_data(self, client, mock_kafka_producer):
        """Test notification event with minimal required data."""
        base_data = create_os_event_base_data()
        base_data.update(
            {"notification_id": "notif_minimal", "app_identifier": "com.example.app"},
        )

        response = client.post("/os-events/notifications", json=base_data)
        assert response.status_code == 201

    def test_upload_notification_event_missing_required_fields(self, client):
        """Test notification event with missing required fields."""
        test_data = create_notification_test_data()
        del test_data["notification_id"]

        response = client.post("/os-events/notifications", json=test_data)
        assert response.status_code == 422

    def test_upload_notification_event_kafka_failure(self, client):
        """Test notification event when Kafka fails."""
        with patch("app.routers.os_events.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_notification_test_data()
            response = client.post("/os-events/notifications", json=test_data)

            assert response.status_code == 500
            assert "Failed to process notification event" in response.json()["detail"]


class TestOSEventTypes:
    """Test OS event types information endpoint."""

    def test_get_event_types_success(self, client):
        """Test successful retrieval of event types."""
        response = client.get("/os-events/event-types")

        assert response.status_code == 200
        data = response.json()

        # Check that all main categories are present
        assert "app_lifecycle" in data
        assert "system" in data
        assert "notifications" in data

        # Check app lifecycle structure
        app_lifecycle = data["app_lifecycle"]
        assert "description" in app_lifecycle
        assert "event_types" in app_lifecycle
        assert "topic" in app_lifecycle
        assert app_lifecycle["topic"] == "os.events.app_lifecycle.raw"

        # Check that required event types are present
        required_app_events = [
            "launch",
            "foreground",
            "background",
            "terminate",
            "crash",
        ]
        for event_type in required_app_events:
            assert event_type in app_lifecycle["event_types"]

        # Check system events structure
        system = data["system"]
        assert "description" in system
        assert "event_types" in system
        assert "event_categories" in system
        assert "topic" in system
        assert system["topic"] == "os.events.system.raw"

        # Check that required system event types are present
        required_system_events = [
            "screen_on",
            "screen_off",
            "device_lock",
            "device_unlock",
            "power_connected",
            "power_disconnected",
        ]
        for event_type in required_system_events:
            assert event_type in system["event_types"]

        # Check that event categories are present
        required_categories = ["system", "power", "screen", "lock"]
        for category in required_categories:
            assert category in system["event_categories"]

        # Check notifications structure
        notifications = data["notifications"]
        assert "description" in notifications
        assert "actions" in notifications
        assert "topic" in notifications
        assert notifications["topic"] == "os.events.notifications.raw"

        # Check notification actions
        required_actions = ["posted", "removed", "clicked"]
        for action in required_actions:
            assert action in notifications["actions"]


class TestOSEventModels:
    """Test OS event model validation."""

    def test_app_lifecycle_model_validation(self):
        """Test app lifecycle model validation."""
        valid_data = create_app_lifecycle_test_data()
        model = OSEventAppLifecycle(**valid_data)

        assert model.app_identifier == "com.example.testapp"
        assert model.event_type == "launch"
        assert model.duration_seconds == 120

    def test_system_event_model_validation(self):
        """Test system event model validation."""
        valid_data = create_system_event_test_data()
        model = OSEventSystemRaw(**valid_data)

        assert model.event_type == "screen_on"
        assert model.event_category == "screen"
        assert model.severity == "info"

    def test_notification_model_validation(self):
        """Test notification model validation."""
        valid_data = create_notification_test_data()
        model = OSEventNotification(**valid_data)

        assert model.notification_id == "notif_12345"
        assert model.app_identifier == "com.example.messenger"
        assert model.action == "posted"

    def test_model_device_id_validation(self):
        """Test device_id validation across all OS event models."""
        # Test with invalid device_id
        invalid_data = create_app_lifecycle_test_data()
        invalid_data["device_id"] = "invalid-uuid"

        with pytest.raises(ValueError, match="device_id must be a valid UUID format"):
            OSEventAppLifecycle(**invalid_data)

    def test_model_recorded_at_validation(self):
        """Test recorded_at validation across all OS event models."""
        # Test with missing recorded_at
        invalid_data = create_app_lifecycle_test_data()
        del invalid_data["recorded_at"]

        with pytest.raises(ValueError, match="Field required"):
            OSEventAppLifecycle(**invalid_data)


class TestOSEventSchemaValidation:
    """Test comprehensive schema validation for OS events."""

    def test_app_lifecycle_schema_completeness(self, client, mock_kafka_producer):
        """Test that app lifecycle schema accepts all expected fields."""
        comprehensive_data = create_app_lifecycle_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_12345",
                "services_encountered": ["ingestion-api"],
                "metadata": {
                    "app_version": "2.1.0",
                    "session_duration": 300,
                    "memory_usage": "45MB",
                    "crash_reason": None,
                    "user_interaction": True,
                },
            },
        )

        response = client.post("/os-events/app-lifecycle", json=comprehensive_data)
        assert response.status_code == 201

    def test_system_event_schema_completeness(self, client, mock_kafka_producer):
        """Test that system event schema accepts all expected fields."""
        comprehensive_data = create_system_event_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_12345",
                "services_encountered": ["ingestion-api"],
                "severity": "warning",
                "description": "Detailed system event description",
                "metadata": {
                    "battery_level": 45,
                    "temperature": 22.5,
                    "network_state": "connected",
                    "user_present": True,
                },
            },
        )

        response = client.post("/os-events/system", json=comprehensive_data)
        assert response.status_code == 201

    def test_notification_schema_completeness(self, client, mock_kafka_producer):
        """Test that notification schema accepts all expected fields."""
        comprehensive_data = create_notification_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_12345",
                "services_encountered": ["ingestion-api"],
                "title": "Full notification title with emoji 📱",
                "body": "Complete notification body with multiple lines\nand special characters: @#$%",
                "metadata": {
                    "notification_group": "messaging",
                    "auto_cancel": True,
                    "large_icon": True,
                    "actions": ["reply", "mark_read"],
                    "timestamp": "2024-01-15T10:30:00Z",
                },
            },
        )

        response = client.post("/os-events/notifications", json=comprehensive_data)
        assert response.status_code == 201
