"""Enhanced unit tests for sensor ingestion endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_helpers import generate_test_device_id, generate_test_recorded_at


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.sensors.kafka_producer") as mock:
        mock.send_sensor_data = AsyncMock()
        mock.send_audio_chunk = AsyncMock()
        mock.send_image_data = AsyncMock()
        yield mock


class TestGPSEnhanced:
    """Enhanced tests for GPS sensor endpoint."""

    def test_gps_success_minimal(self, client, mock_kafka_producer):
        """Test GPS with minimal required data."""
        gps_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "latitude": 37.7749,
            "longitude": -122.4194,
        }

        response = client.post("/sensor/gps", json=gps_data)
        assert response.status_code == 201

    def test_gps_success_full_data(self, client, mock_kafka_producer):
        """Test GPS with all optional fields."""
        gps_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 100.5,
            "accuracy": 5.0,
            "heading": 45.0,
            "speed": 2.5,
        }

        response = client.post("/sensor/gps", json=gps_data)
        assert response.status_code == 201
        assert response.json()["topic"] == "device.sensor.gps.raw"

    def test_gps_boundary_coordinates(self, client, mock_kafka_producer):
        """Test GPS with boundary coordinate values."""
        boundary_cases = [
            {"latitude": 90.0, "longitude": 180.0},  # Max values
            {"latitude": -90.0, "longitude": -180.0},  # Min values
            {"latitude": 0.0, "longitude": 0.0},  # Zero values
        ]

        for coords in boundary_cases:
            gps_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                **coords,
            }
            response = client.post("/sensor/gps", json=gps_data)
            assert response.status_code == 201

    def test_gps_invalid_coordinates(self, client, mock_kafka_producer):
        """Test GPS with coordinate values outside normal range succeeds (no validation)."""
        invalid_cases = [
            {"latitude": 91.0, "longitude": 0.0},  # Lat too high
            {"latitude": -91.0, "longitude": 0.0},  # Lat too low
            {"latitude": 0.0, "longitude": 181.0},  # Lng too high
            {"latitude": 0.0, "longitude": -181.0},  # Lng too low
        ]

        for coords in invalid_cases:
            gps_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                **coords,
            }
            response = client.post("/sensor/gps", json=gps_data)
            assert response.status_code == 201


class TestAccelerometerEnhanced:
    """Enhanced tests for accelerometer sensor endpoint."""

    def test_accelerometer_success(self, client, mock_kafka_producer):
        """Test accelerometer with normal data."""
        accel_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "x": 0.5,
            "y": -0.2,
            "z": 9.8,
        }

        response = client.post("/sensor/accelerometer", json=accel_data)
        assert response.status_code == 201
        assert response.json()["topic"] == "device.sensor.accelerometer.raw"

    def test_accelerometer_extreme_values(self, client, mock_kafka_producer):
        """Test accelerometer with extreme values."""
        extreme_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "x": 100.0,
            "y": -100.0,
            "z": 0.0,
        }

        response = client.post("/sensor/accelerometer", json=extreme_data)
        assert response.status_code == 201

    def test_accelerometer_precision(self, client, mock_kafka_producer):
        """Test accelerometer with high precision values."""
        precise_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "x": 0.123456789,
            "y": -0.987654321,
            "z": 9.806650000,
        }

        response = client.post("/sensor/accelerometer", json=precise_data)
        assert response.status_code == 201


class TestHeartRateEnhanced:
    """Enhanced tests for heart rate sensor endpoint."""

    def test_heartrate_success_minimal(self, client, mock_kafka_producer):
        """Test heart rate with minimal data."""
        hr_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "bpm": 72,
        }

        response = client.post("/sensor/heartrate", json=hr_data)
        assert response.status_code == 201
        assert response.json()["topic"] == "device.health.heartrate.raw"

    def test_heartrate_with_confidence(self, client, mock_kafka_producer):
        """Test heart rate with confidence value."""
        hr_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "bpm": 85,
            "confidence": 0.95,
        }

        response = client.post("/sensor/heartrate", json=hr_data)
        assert response.status_code == 201

    def test_heartrate_range_validation(self, client, mock_kafka_producer):
        """Test heart rate with various BPM values."""
        valid_bpm_values = [40, 60, 80, 100, 120, 180, 220]

        for bpm in valid_bpm_values:
            hr_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "bpm": bpm,
            }
            response = client.post("/sensor/heartrate", json=hr_data)
            assert response.status_code == 201

    def test_heartrate_invalid_bpm(self, client, mock_kafka_producer):
        """Test heart rate with extreme BPM values succeeds (no validation)."""
        invalid_bpm_values = [0, -10, 1000]

        for bpm in invalid_bpm_values:
            hr_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "bpm": bpm,
            }
            response = client.post("/sensor/heartrate", json=hr_data)
            assert response.status_code == 201

    def test_heartrate_confidence_validation(self, client, mock_kafka_producer):
        """Test heart rate confidence validation."""
        # Valid confidence values
        valid_confidences = [0.0, 0.5, 1.0]
        for conf in valid_confidences:
            hr_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "bpm": 72,
                "confidence": conf,
            }
            response = client.post("/sensor/heartrate", json=hr_data)
            assert response.status_code == 201

        # Invalid confidence values (no validation, should succeed)
        invalid_confidences = [-0.1, 1.1, 2.0]
        for conf in invalid_confidences:
            hr_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "bpm": 72,
                "confidence": conf,
            }
            response = client.post("/sensor/heartrate", json=hr_data)
            assert response.status_code == 201


class TestPowerStateEnhanced:
    """Enhanced tests for power state endpoint."""

    def test_power_state_success(self, client, mock_kafka_producer):
        """Test power state with full data."""
        power_data = {
            "device_id": generate_test_device_id(),
            "recorded_at": generate_test_recorded_at(),
            "battery_level": 85.5,
            "is_charging": True,
            "power_source": "AC",
        }

        response = client.post("/sensor/power", json=power_data)
        assert response.status_code == 201
        assert response.json()["topic"] == "device.state.power.raw"

    def test_power_state_battery_levels(self, client, mock_kafka_producer):
        """Test power state with various battery levels."""
        battery_levels = [0.0, 25.5, 50.0, 75.25, 100.0]

        for level in battery_levels:
            power_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "battery_level": level,
                "is_charging": False,
            }
            response = client.post("/sensor/power", json=power_data)
            assert response.status_code == 201

    def test_power_state_invalid_battery(self, client, mock_kafka_producer):
        """Test power state with out-of-range battery levels succeeds (no validation)."""
        invalid_levels = [-1.0, 100.1, 200.0]

        for level in invalid_levels:
            power_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "battery_level": level,
                "is_charging": False,
            }
            response = client.post("/sensor/power", json=power_data)
            assert response.status_code == 201

    def test_power_state_charging_scenarios(self, client, mock_kafka_producer):
        """Test different charging scenarios."""
        scenarios = [
            {"is_charging": True, "power_source": "AC"},
            {"is_charging": True, "power_source": "USB"},
            {"is_charging": True, "power_source": "Wireless"},
            {"is_charging": False, "power_source": None},
        ]

        for scenario in scenarios:
            power_data = {
                "device_id": generate_test_device_id(),
                "recorded_at": generate_test_recorded_at(),
                "battery_level": 50.0,
                **scenario,
            }
            response = client.post("/sensor/power", json=power_data)
            assert response.status_code == 201


class TestSensorBatch:
    """Test sensor batch upload endpoint."""

    def test_sensor_batch_success(self, client, mock_kafka_producer):
        """Test successful batch sensor upload."""
        device_id = generate_test_device_id()
        recorded_at = generate_test_recorded_at()
        sensors = [
            {
                "device_id": device_id,
                "recorded_at": recorded_at,
                "sensor_type": "gps",
                "value": {"latitude": 37.7749, "longitude": -122.4194},
                "accuracy": 5.0,
            },
            {
                "device_id": device_id,
                "recorded_at": recorded_at,
                "sensor_type": "accelerometer",
                "value": {"x": 0.1, "y": 0.2, "z": 9.8},
                "unit": "m/s²",
            },
            {
                "device_id": device_id,
                "recorded_at": recorded_at,
                "sensor_type": "temperature",
                "value": {"celsius": 23.5},
                "unit": "°C",
            },
        ]

        response = client.post("/sensor/batch", json=sensors)
        assert response.status_code == 201

        # Verify all sensors were processed
        assert mock_kafka_producer.send_sensor_data.call_count == 3

    def test_sensor_batch_too_large(self, client, mock_kafka_producer):
        """Test batch upload with many sensors succeeds (no size limit)."""
        sensors = []
        device_id = generate_test_device_id()
        recorded_at = generate_test_recorded_at()
        for i in range(101):  # Large batch
            sensors.append(
                {
                    "device_id": device_id,
                    "recorded_at": recorded_at,
                    "sensor_type": "test",
                    "value": {"reading": i},
                },
            )

        response = client.post("/sensor/batch", json=sensors)
        assert response.status_code == 201
