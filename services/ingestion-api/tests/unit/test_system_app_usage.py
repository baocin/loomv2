"""Unit tests for system app usage endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models import (
    AndroidAppCategoryStats,
    AndroidAppEvent,
    AndroidAppUsageAggregated,
)


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.system.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        yield mock


def create_app_usage_base_data() -> dict:
    """Create base test data for app usage endpoints."""
    from ..test_helpers import create_base_test_data

    return create_base_test_data()


def create_android_app_event_test_data() -> dict:
    """Create test data for individual Android app events."""
    base_data = create_app_usage_base_data()
    base_data.update(
        {
            "package_name": "com.example.testapp",
            "app_name": "Test App",
            "event_type": "MOVE_TO_FOREGROUND",
            "class_name": "com.example.testapp.MainActivity",
            "configuration": {
                "orientation": "portrait",
                "density": 3.0,
                "screen_size": "normal",
            },
            "shortcut_id": "test_shortcut",
            "standby_bucket": 2,
            "notification_channel_id": "default",
            "metadata": {
                "version_code": 123,
                "version_name": "1.2.3",
                "process_importance": "foreground",
            },
        },
    )
    return base_data


def create_android_app_category_stats_test_data() -> dict:
    """Create test data for Android app category statistics."""
    base_data = create_app_usage_base_data()
    base_data.update(
        {
            "aggregation_period_start": "2024-01-15T00:00:00Z",
            "aggregation_period_end": "2024-01-15T23:59:59Z",
            "total_screen_time_ms": 28800000,  # 8 hours
            "device_unlocks": 45,
            "category_stats": [
                {
                    "category": "SOCIAL",
                    "total_time_ms": 14400000,  # 4 hours
                    "app_count": 3,
                    "percentage_of_total": 50.0,
                },
                {
                    "category": "PRODUCTIVITY",
                    "total_time_ms": 7200000,  # 2 hours
                    "app_count": 5,
                    "percentage_of_total": 25.0,
                },
                {
                    "category": "ENTERTAINMENT",
                    "total_time_ms": 7200000,  # 2 hours
                    "app_count": 2,
                    "percentage_of_total": 25.0,
                },
            ],
            "metadata": {
                "data_source": "UsageStatsManager",
                "collection_method": "aggregated_daily",
                "device_model": "Pixel 7",
            },
        },
    )
    return base_data


def create_android_app_usage_aggregated_test_data() -> dict:
    """Create test data for pre-aggregated Android app usage."""
    base_data = create_app_usage_base_data()
    base_data.update(
        {
            "aggregation_period_start": "2024-01-15T00:00:00Z",
            "aggregation_period_end": "2024-01-15T23:59:59Z",
            "aggregation_interval_minutes": 60,
            "total_screen_time_ms": 28800000,  # 8 hours
            "total_unlocks": 45,
            "app_usage_stats": [
                {
                    "package_name": "com.instagram.android",
                    "app_name": "Instagram",
                    "total_time_foreground_ms": 7200000,  # 2 hours
                    "last_time_used": "2024-01-15T22:30:00Z",
                    "total_time_foreground_service_used_ms": 0,
                    "launch_count": 12,
                },
                {
                    "package_name": "com.spotify.music",
                    "app_name": "Spotify",
                    "total_time_foreground_ms": 3600000,  # 1 hour
                    "last_time_used": "2024-01-15T23:45:00Z",
                    "total_time_foreground_service_used_ms": 14400000,  # 4 hours background
                    "launch_count": 3,
                },
            ],
            "app_event_stats": [
                {
                    "package_name": "com.instagram.android",
                    "event_type": "MOVE_TO_FOREGROUND",
                    "event_count": 12,
                    "last_event_time": "2024-01-15T22:30:00Z",
                },
                {
                    "package_name": "com.instagram.android",
                    "event_type": "MOVE_TO_BACKGROUND",
                    "event_count": 12,
                    "last_event_time": "2024-01-15T22:35:00Z",
                },
            ],
            "screen_time_by_category": [
                {
                    "category": "SOCIAL",
                    "total_time_ms": 14400000,
                    "app_count": 3,
                    "percentage_of_total": 50.0,
                },
            ],
            "notification_stats": [
                {
                    "package_name": "com.instagram.android",
                    "notification_count": 23,
                    "interaction_count": 8,
                    "dismissal_count": 15,
                },
            ],
        },
    )
    return base_data


class TestAndroidAppEventEndpoint:
    """Test individual Android app event endpoint."""

    def test_upload_android_app_event_success(self, client, mock_kafka_producer):
        """Test successful Android app event upload."""
        test_data = create_android_app_event_test_data()

        response = client.post("/system/apps/android/events", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.app_usage.android.events"
        assert data["event"]["package_name"] == "com.example.testapp"
        assert data["event"]["event_type"] == "MOVE_TO_FOREGROUND"
        assert "message_id" in data

        # Verify Kafka producer was called
        mock_kafka_producer.send_message.assert_called_once()
        call_args = mock_kafka_producer.send_message.call_args
        assert call_args[1]["topic"] == "device.app_usage.android.events"
        assert call_args[1]["key"] == test_data["device_id"]

    def test_upload_android_app_event_all_types(self, client, mock_kafka_producer):
        """Test all supported Android app event types."""
        event_types = [
            "MOVE_TO_FOREGROUND",
            "MOVE_TO_BACKGROUND",
            "ACTIVITY_PAUSED",
            "ACTIVITY_RESUMED",
            "APP_COMPONENT_USED",
            "CONFIGURATION_CHANGE",
            "USER_INTERACTION",
            "SHORTCUT_INVOCATION",
            "CHOOSER_ACTION",
            "NOTIFICATION_INTERRUPTION",
        ]

        for event_type in event_types:
            test_data = create_android_app_event_test_data()
            test_data["event_type"] = event_type

            response = client.post("/system/apps/android/events", json=test_data)

            assert response.status_code == 201
            data = response.json()
            assert data["event"]["event_type"] == event_type

    def test_upload_android_app_event_minimal_data(self, client, mock_kafka_producer):
        """Test Android app event with minimal required data."""
        base_data = create_app_usage_base_data()
        base_data.update(
            {"package_name": "com.example.minimal", "event_type": "MOVE_TO_FOREGROUND"},
        )

        response = client.post("/system/apps/android/events", json=base_data)
        assert response.status_code == 201

    def test_upload_android_app_event_missing_required_fields(self, client):
        """Test Android app event with missing required fields."""
        test_data = create_android_app_event_test_data()
        del test_data["package_name"]

        response = client.post("/system/apps/android/events", json=test_data)
        assert response.status_code == 422

    def test_upload_android_app_event_app_monitoring_disabled(self, client):
        """Test Android app event when app monitoring is disabled."""
        with patch("app.routers.system.settings") as mock_settings:
            mock_settings.app_monitoring_enabled = False

            test_data = create_android_app_event_test_data()
            response = client.post("/system/apps/android/events", json=test_data)

            assert response.status_code == 503
            assert "App monitoring is currently disabled" in response.json()["detail"]

    def test_upload_android_app_event_kafka_failure(self, client):
        """Test Android app event when Kafka fails."""
        with patch("app.routers.system.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_android_app_event_test_data()
            response = client.post("/system/apps/android/events", json=test_data)

            assert response.status_code == 500
            assert "Failed to process Android app event" in response.json()["detail"]


class TestAndroidAppCategoryStatsEndpoint:
    """Test Android app category statistics endpoint."""

    def test_upload_android_category_stats_success(self, client, mock_kafka_producer):
        """Test successful Android category stats upload."""
        test_data = create_android_app_category_stats_test_data()

        response = client.post("/system/apps/android/categories", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.app_usage.android.categories"
        assert data["aggregation_period"]["start"] == "2024-01-15T00:00:00+00:00"
        assert data["aggregation_period"]["end"] == "2024-01-15T23:59:59+00:00"
        assert data["stats"]["total_screen_time_ms"] == 28800000
        assert data["stats"]["category_count"] == 3
        assert data["stats"]["device_unlocks"] == 45
        assert "message_id" in data

    def test_upload_android_category_stats_various_categories(
        self,
        client,
        mock_kafka_producer,
    ):
        """Test category stats with various app categories."""
        categories = [
            "SOCIAL",
            "PRODUCTIVITY",
            "ENTERTAINMENT",
            "EDUCATION",
            "GAME",
            "COMMUNICATION",
            "MUSIC_AND_AUDIO",
            "VIDEO",
            "SHOPPING",
            "TOOLS",
        ]

        test_data = create_android_app_category_stats_test_data()
        # Update with more categories
        test_data["category_stats"] = [
            {
                "category": category,
                "total_time_ms": 1000000,  # ~17 minutes each
                "app_count": 2,
                "percentage_of_total": 10.0,
            }
            for category in categories[:5]  # Test with 5 categories
        ]

        response = client.post("/system/apps/android/categories", json=test_data)
        assert response.status_code == 201

    def test_upload_android_category_stats_edge_case_percentages(
        self,
        client,
        mock_kafka_producer,
    ):
        """Test category stats with edge case percentage values."""
        test_data = create_android_app_category_stats_test_data()
        test_data["category_stats"] = [
            {
                "category": "SOCIAL",
                "total_time_ms": 0,
                "app_count": 0,
                "percentage_of_total": 0.0,
            },
            {
                "category": "PRODUCTIVITY",
                "total_time_ms": 28800000,
                "app_count": 1,
                "percentage_of_total": 100.0,
            },
        ]

        response = client.post("/system/apps/android/categories", json=test_data)
        assert response.status_code == 201

    def test_upload_android_category_stats_invalid_percentage(self, client):
        """Test category stats with invalid percentage values."""
        test_data = create_android_app_category_stats_test_data()
        test_data["category_stats"][0]["percentage_of_total"] = 150.0  # Invalid > 100%

        response = client.post("/system/apps/android/categories", json=test_data)
        assert response.status_code == 422

    def test_upload_android_category_stats_missing_required_fields(self, client):
        """Test category stats with missing required fields."""
        test_data = create_android_app_category_stats_test_data()
        del test_data["aggregation_period_start"]

        response = client.post("/system/apps/android/categories", json=test_data)
        assert response.status_code == 422

    def test_upload_android_category_stats_app_monitoring_disabled(self, client):
        """Test category stats when app monitoring is disabled."""
        with patch("app.routers.system.settings") as mock_settings:
            mock_settings.app_monitoring_enabled = False

            test_data = create_android_app_category_stats_test_data()
            response = client.post("/system/apps/android/categories", json=test_data)

            assert response.status_code == 503

    def test_upload_android_category_stats_kafka_failure(self, client):
        """Test category stats when Kafka fails."""
        with patch("app.routers.system.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_android_app_category_stats_test_data()
            response = client.post("/system/apps/android/categories", json=test_data)

            assert response.status_code == 500
            assert (
                "Failed to process Android category stats" in response.json()["detail"]
            )


class TestAndroidAppUsageAggregatedEndpoint:
    """Test pre-aggregated Android app usage endpoint."""

    def test_upload_android_usage_stats_success(self, client, mock_kafka_producer):
        """Test successful Android usage stats upload."""
        test_data = create_android_app_usage_aggregated_test_data()

        response = client.post("/system/apps/android/usage", json=test_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.app_usage.android.aggregated"
        assert data["aggregation_period"]["start"] == "2024-01-15T00:00:00+00:00"
        assert data["aggregation_period"]["end"] == "2024-01-15T23:59:59+00:00"
        assert data["stats"]["total_screen_time_ms"] == 28800000
        assert data["stats"]["app_count"] == 2
        assert data["stats"]["event_count"] == 2

    def test_upload_android_usage_stats_comprehensive_data(
        self,
        client,
        mock_kafka_producer,
    ):
        """Test usage stats with comprehensive nested data structures."""
        test_data = create_android_app_usage_aggregated_test_data()

        # Add more comprehensive data
        test_data["app_usage_stats"].append(
            {
                "package_name": "com.google.android.apps.docs",
                "app_name": "Google Docs",
                "total_time_foreground_ms": 1800000,  # 30 minutes
                "last_time_used": "2024-01-15T16:20:00Z",
                "last_time_foreground_service_used": "2024-01-15T16:25:00Z",
                "total_time_foreground_service_used_ms": 900000,  # 15 minutes
                "launch_count": 5,
            },
        )

        response = client.post("/system/apps/android/usage", json=test_data)
        assert response.status_code == 201

    def test_upload_android_usage_stats_empty_arrays(self, client, mock_kafka_producer):
        """Test usage stats with empty arrays for optional fields."""
        test_data = create_android_app_usage_aggregated_test_data()
        test_data.update(
            {
                "app_event_stats": [],
                "screen_time_by_category": [],
                "notification_stats": [],
            },
        )

        response = client.post("/system/apps/android/usage", json=test_data)
        assert response.status_code == 201

    def test_upload_android_usage_stats_invalid_time_period(self, client):
        """Test usage stats with invalid time period (end before start)."""
        test_data = create_android_app_usage_aggregated_test_data()
        test_data["aggregation_period_end"] = "2024-01-14T23:59:59Z"  # Before start

        response = client.post("/system/apps/android/usage", json=test_data)
        assert response.status_code == 422

    def test_upload_android_usage_stats_too_many_apps(self, client):
        """Test usage stats with too many app entries."""
        test_data = create_android_app_usage_aggregated_test_data()

        # Create 501 app entries (over the 500 limit)
        large_app_list = []
        for i in range(501):
            large_app_list.append(
                {
                    "package_name": f"com.example.app{i}",
                    "app_name": f"Test App {i}",
                    "total_time_foreground_ms": 1000,
                    "last_time_used": "2024-01-15T12:00:00Z",
                    "launch_count": 1,
                },
            )

        test_data["app_usage_stats"] = large_app_list

        response = client.post("/system/apps/android/usage", json=test_data)
        assert response.status_code == 422

    def test_upload_android_usage_stats_app_monitoring_disabled(self, client):
        """Test usage stats when app monitoring is disabled."""
        with patch("app.routers.system.settings") as mock_settings:
            mock_settings.app_monitoring_enabled = False

            test_data = create_android_app_usage_aggregated_test_data()
            response = client.post("/system/apps/android/usage", json=test_data)

            assert response.status_code == 503

    def test_upload_android_usage_stats_kafka_failure(self, client):
        """Test usage stats when Kafka fails."""
        with patch("app.routers.system.kafka_producer") as mock_kafka:
            mock_kafka.send_message.side_effect = Exception("Kafka connection failed")

            test_data = create_android_app_usage_aggregated_test_data()
            response = client.post("/system/apps/android/usage", json=test_data)

            assert response.status_code == 500
            assert "Failed to process Android usage stats" in response.json()["detail"]


class TestAppUsageModels:
    """Test app usage model validation."""

    def test_android_app_event_model_validation(self):
        """Test AndroidAppEvent model validation."""
        valid_data = create_android_app_event_test_data()
        model = AndroidAppEvent(**valid_data)

        assert model.package_name == "com.example.testapp"
        assert model.event_type == "MOVE_TO_FOREGROUND"
        assert model.class_name == "com.example.testapp.MainActivity"
        assert model.standby_bucket == 2
        assert model.configuration["orientation"] == "portrait"

    def test_android_app_category_stats_model_validation(self):
        """Test AndroidAppCategoryStats model validation."""
        valid_data = create_android_app_category_stats_test_data()
        model = AndroidAppCategoryStats(**valid_data)

        assert model.total_screen_time_ms == 28800000
        assert model.device_unlocks == 45
        assert len(model.category_stats) == 3
        assert model.category_stats[0].category == "SOCIAL"
        assert model.category_stats[0].percentage_of_total == 50.0

    def test_android_app_usage_aggregated_model_validation(self):
        """Test AndroidAppUsageAggregated model validation."""
        valid_data = create_android_app_usage_aggregated_test_data()
        model = AndroidAppUsageAggregated(**valid_data)

        assert model.aggregation_interval_minutes == 60
        assert model.total_screen_time_ms == 28800000
        assert model.total_unlocks == 45
        assert len(model.app_usage_stats) == 2
        assert len(model.app_event_stats) == 2
        assert model.app_usage_stats[0].package_name == "com.instagram.android"

    def test_model_device_id_validation(self):
        """Test device_id validation across all app usage models."""
        invalid_data = create_android_app_event_test_data()
        invalid_data["device_id"] = "invalid-uuid"

        with pytest.raises(ValueError, match="device_id must be a valid UUID format"):
            AndroidAppEvent(**invalid_data)

    def test_model_recorded_at_validation(self):
        """Test recorded_at validation across all app usage models."""
        invalid_data = create_android_app_event_test_data()
        del invalid_data["recorded_at"]

        with pytest.raises(ValueError, match="Field required"):
            AndroidAppEvent(**invalid_data)


class TestAppUsageSchemaValidation:
    """Test comprehensive schema validation for app usage endpoints."""

    def test_android_app_event_schema_completeness(self, client, mock_kafka_producer):
        """Test that app event schema accepts all expected fields."""
        comprehensive_data = create_android_app_event_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_app_event_12345",
                "services_encountered": ["ingestion-api", "mobile-client"],
                "configuration": {
                    "orientation": "landscape",
                    "density": 3.0,
                    "screen_size": "large",
                    "dark_mode": True,
                    "locale": "en_US",
                },
                "metadata": {
                    "user_id": "user_123",
                    "session_id": "session_456",
                    "app_version": "2.1.0",
                    "build_number": 123,
                    "memory_usage_mb": 45,
                    "cpu_usage_percent": 12.5,
                    "network_type": "wifi",
                    "battery_level": 85,
                },
            },
        )

        response = client.post("/system/apps/android/events", json=comprehensive_data)
        assert response.status_code == 201

    def test_android_category_stats_schema_completeness(
        self,
        client,
        mock_kafka_producer,
    ):
        """Test that category stats schema accepts all expected fields."""
        comprehensive_data = create_android_app_category_stats_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_category_stats_12345",
                "services_encountered": ["ingestion-api", "mobile-client"],
                "metadata": {
                    "collection_method": "usage_stats_api",
                    "data_quality_score": 0.95,
                    "privacy_level": "aggregated",
                    "timezone": "America/Los_Angeles",
                    "locale": "en_US",
                    "device_info": {
                        "manufacturer": "Google",
                        "model": "Pixel 7",
                        "android_version": "14",
                        "api_level": 34,
                    },
                },
            },
        )

        response = client.post(
            "/system/apps/android/categories",
            json=comprehensive_data,
        )
        assert response.status_code == 201

    def test_android_usage_aggregated_schema_completeness(
        self,
        client,
        mock_kafka_producer,
    ):
        """Test that usage aggregated schema accepts all expected fields."""
        comprehensive_data = create_android_app_usage_aggregated_test_data()
        comprehensive_data.update(
            {
                "trace_id": "trace_usage_aggregated_12345",
                "services_encountered": [
                    "ingestion-api",
                    "mobile-client",
                    "usage-processor",
                ],
            },
        )

        # Add more comprehensive app usage stats
        comprehensive_data["app_usage_stats"][0].update(
            {"last_time_foreground_service_used": "2024-01-15T22:25:00Z"},
        )

        response = client.post("/system/apps/android/usage", json=comprehensive_data)
        assert response.status_code == 201
