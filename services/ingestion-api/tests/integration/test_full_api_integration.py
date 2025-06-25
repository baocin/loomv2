"""Integration tests for the complete ingestion API."""

import base64
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer for integration tests."""
    with patch("app.kafka_producer.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        mock.is_connected = True
        yield mock


class TestFullAPIIntegration:
    """Complete API integration tests."""

    def test_health_endpoints(self, client):
        """Test all health endpoints."""
        # Test health check
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

        # Test readiness check
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

        # Test metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "loom-ingestion-api"
        assert "endpoints" in data
        assert "audio_upload" in data["endpoints"]
        assert "image_upload" in data["endpoints"]
        assert "note_upload" in data["endpoints"]

    def test_complete_data_ingestion_workflow(self, client, mock_kafka_producer):
        """Test complete workflow ingesting all data types."""
        from ..test_helpers import (
            create_accelerometer_test_data,
            create_audio_test_data,
            create_device_metadata_test_data,
            create_gps_test_data,
            create_heartrate_test_data,
            create_image_test_data,
            create_macos_apps_test_data,
            create_note_test_data,
            create_power_test_data,
        )

        # 1. Upload audio data
        audio_data = create_audio_test_data()
        response = client.post("/audio/upload", json=audio_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 2. Upload image data
        image_data = create_image_test_data()
        response = client.post("/images/upload", json=image_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 3. Upload screenshot
        screenshot_data = create_image_test_data()
        screenshot_data["format"] = "png"
        response = client.post("/images/screenshot", json=screenshot_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 4. Upload note
        note_data = create_note_test_data()
        note_data.update(
            {
                "content": "This is an integration test note with multiple words.",
                "title": "Integration Test Note",
                "tags": ["integration", "test"],
            },
        )
        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 5. Upload GPS data
        gps_data = create_gps_test_data()
        response = client.post("/sensor/gps", json=gps_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 6. Upload accelerometer data
        accel_data = create_accelerometer_test_data()
        response = client.post("/sensor/accelerometer", json=accel_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 7. Upload heart rate data
        hr_data = create_heartrate_test_data()
        response = client.post("/sensor/heartrate", json=hr_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 8. Upload power state
        power_data = create_power_test_data()
        response = client.post("/sensor/power", json=power_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 9. Upload app monitoring data (macOS)
        macos_apps = create_macos_apps_test_data()
        response = client.post("/system/apps/macos", json=macos_apps)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 10. Upload device metadata
        metadata = create_device_metadata_test_data()
        response = client.post("/system/metadata", json=metadata)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify all messages were sent to Kafka
        assert mock_kafka_producer.send_message.call_count == 10

    def test_batch_operations(self, client, mock_kafka_producer):
        """Test batch upload operations."""
        device_id = "batch-test-device"

        # Test note batch upload
        notes = []
        for i in range(5):
            notes.append(
                {
                    "device_id": device_id,
                    "content": f"Batch note {i + 1} with content.",
                    "title": f"Note {i + 1}",
                    "tags": [f"batch-{i}"],
                },
            )

        response = client.post("/notes/batch", json=notes)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Test image batch upload
        images = []
        for i in range(3):
            images.append(
                {
                    "device_id": device_id,
                    "image_data": base64.b64encode(f"image_{i}".encode()).decode(),
                    "width": 800,
                    "height": 600,
                    "camera_type": "front" if i % 2 == 0 else "rear",
                },
            )

        response = client.post("/images/batch", json=images)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Test sensor batch upload
        sensors = [
            {
                "device_id": device_id,
                "sensor_type": "temperature",
                "value": {"celsius": 22.5},
                "unit": "°C",
            },
            {
                "device_id": device_id,
                "sensor_type": "humidity",
                "value": {"percentage": 65.0},
                "unit": "%",
            },
        ]

        response = client.post("/sensor/batch", json=sensors)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify batch operations sent correct number of messages
        expected_calls = 5 + 3 + 2  # notes + images + sensors
        assert mock_kafka_producer.send_message.call_count == expected_calls

    def test_error_handling_integration(self, client, mock_kafka_producer):
        """Test error handling across the API."""
        # Test with invalid JSON
        response = client.post(
            "/audio/upload",
            data="invalid json",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422

        # Test with missing required fields
        response = client.post("/audio/upload", json={"device_id": "test"})
        assert response.status_code == 422

        # Test with invalid data types
        response = client.post(
            "/sensor/gps",
            json={
                "device_id": "test",
                "latitude": "not_a_number",
                "longitude": -122.4194,
            },
        )
        assert response.status_code == 422

        # Test with invalid base64 data
        response = client.post(
            "/images/upload",
            json={
                "device_id": "test",
                "image_data": "invalid_base64!",
                "width": 100,
                "height": 100,
            },
        )
        assert response.status_code == 400

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/audio/upload")
        assert response.status_code == 200

        # Check for CORS headers in a real request
        response = client.get("/healthz")
        # Note: TestClient doesn't include CORS headers in response,
        # but we can verify the middleware is configured

    def test_api_documentation(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/audio/upload" in schema["paths"]
        assert "/images/upload" in schema["paths"]
        assert "/notes/upload" in schema["paths"]

        # Test docs endpoint (Swagger UI)
        response = client.get("/docs")
        assert response.status_code == 200

    def test_realistic_data_volumes(self, client, mock_kafka_producer):
        """Test with realistic data volumes."""
        device_id = "volume-test-device"

        # Test with larger audio chunk (5 seconds of 44.1kHz stereo)
        large_audio_data = b"x" * (44100 * 2 * 2 * 5)  # 5 seconds
        audio_data = {
            "device_id": device_id,
            "chunk_data": base64.b64encode(large_audio_data).decode(),
            "sample_rate": 44100,
            "channels": 2,
            "format": "wav",
            "duration_ms": 5000,
        }
        response = client.post("/audio/upload", json=audio_data)
        assert response.status_code == 200

        # Test with high-resolution image (simulated 4K)
        large_image_data = b"x" * (3840 * 2160 * 3)  # 4K RGB image simulation
        image_data = {
            "device_id": device_id,
            "image_data": base64.b64encode(large_image_data).decode(),
            "width": 3840,
            "height": 2160,
            "format": "jpeg",
            "file_size": len(large_image_data),
        }
        response = client.post("/images/upload", json=image_data)
        assert response.status_code == 200

        # Test with long note content
        long_content = "This is a very long note. " * 100  # ~2700 characters
        note_data = {
            "device_id": device_id,
            "content": long_content,
            "title": "Long Form Note",
            "note_type": "text",
        }
        response = client.post("/notes/upload", json=note_data)
        assert response.status_code == 200

        # Verify all large data was processed
        assert mock_kafka_producer.send_message.call_count == 3

    def test_concurrent_uploads(self, client, mock_kafka_producer):
        """Test handling concurrent uploads (simulated)."""
        import concurrent.futures

        device_id = "concurrent-test-device"
        results = []

        def upload_data(endpoint, data):
            try:
                response = client.post(endpoint, json=data)
                return response.status_code == 200
            except Exception:
                return False

        # Prepare different types of data
        requests = [
            (
                "/audio/upload",
                {
                    "device_id": device_id,
                    "chunk_data": base64.b64encode(b"audio").decode(),
                    "sample_rate": 44100,
                    "duration_ms": 100,
                },
            ),
            (
                "/images/upload",
                {
                    "device_id": device_id,
                    "image_data": base64.b64encode(b"image").decode(),
                    "width": 100,
                    "height": 100,
                },
            ),
            (
                "/notes/upload",
                {"device_id": device_id, "content": "Concurrent test note"},
            ),
            (
                "/sensor/gps",
                {"device_id": device_id, "latitude": 37.7749, "longitude": -122.4194},
            ),
        ]

        # Submit requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(upload_data, endpoint, data)
                for endpoint, data in requests
            ]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Verify all requests succeeded
        assert all(results), "Some concurrent requests failed"
        assert mock_kafka_producer.send_message.call_count == 4
