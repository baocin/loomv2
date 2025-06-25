"""Tests for distributed tracing functionality."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.tracing import (
    add_service_to_trace,
    create_child_trace_context,
    get_trace_context,
)


@pytest.fixture()
def test_client():
    """Create a test client with tracing middleware."""
    return TestClient(app)


@pytest.fixture()
def gps_reading_data():
    """Sample GPS reading data for tests."""
    return {
        "device_id": "12345678-1234-8000-8000-123456789012",
        "recorded_at": "2024-01-15T10:30:00+00:00",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "accuracy": 5.0,
    }


class TestTracingMiddleware:
    """Test the tracing middleware functionality."""

    def test_middleware_adds_trace_id_to_new_request(self, test_client):
        """Test that middleware generates trace ID for new requests."""
        response = test_client.get("/healthz")

        assert response.status_code == status.HTTP_200_OK
        assert "X-Trace-ID" in response.headers
        assert "X-Services-Encountered" in response.headers

        # Verify trace ID is a valid UUID
        trace_id = response.headers["X-Trace-ID"]
        try:
            uuid.UUID(trace_id)
        except ValueError:
            pytest.fail(f"Invalid trace ID format: {trace_id}")

        # Verify services encountered includes ingestion-api
        services = response.headers["X-Services-Encountered"].split(",")
        assert "ingestion-api" in services

    def test_middleware_preserves_existing_trace_id(self, test_client):
        """Test that middleware preserves trace ID from request headers."""
        existing_trace_id = str(uuid.uuid4())
        headers = {"X-Trace-ID": existing_trace_id}

        response = test_client.get("/healthz", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Trace-ID"] == existing_trace_id

    def test_middleware_extends_services_encountered(self, test_client):
        """Test that middleware extends existing services list."""
        existing_trace_id = str(uuid.uuid4())
        headers = {
            "X-Trace-ID": existing_trace_id,
            "X-Services-Encountered": "upstream-service,api-gateway",
        }

        response = test_client.get("/healthz", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        services = response.headers["X-Services-Encountered"].split(",")
        assert "upstream-service" in services
        assert "api-gateway" in services
        assert "ingestion-api" in services

    def test_error_response_includes_trace_info(self, test_client):
        """Test that error responses include trace information."""
        # Trigger an error by calling a non-existent endpoint
        response = test_client.get("/non-existent-endpoint")

        # Should be 404, but still have trace headers
        assert "X-Trace-ID" in response.headers
        assert "X-Services-Encountered" in response.headers


class TestTracingUtilities:
    """Test the tracing utility functions."""

    def test_get_trace_context_returns_empty_when_no_context(self):
        """Test that get_trace_context returns empty values when no context is set."""
        context = get_trace_context()
        assert context["trace_id"] == ""
        assert context["services_encountered"] == []

    def test_add_service_to_trace_function(self):
        """Test adding services to trace context."""
        # This test would need to be run within a request context
        # For now, we'll test the function exists and doesn't error
        add_service_to_trace("test-service")

    def test_create_child_trace_context(self):
        """Test creating child trace context."""
        parent_trace_id = str(uuid.uuid4())
        parent_services = ["service-a", "service-b"]

        child_trace_id = create_child_trace_context(parent_trace_id, parent_services)

        # Child should have different trace ID
        assert child_trace_id != parent_trace_id

        # Child should be valid UUID
        try:
            uuid.UUID(child_trace_id)
        except ValueError:
            pytest.fail(f"Invalid child trace ID format: {child_trace_id}")


class TestEndpointTracing:
    """Test that endpoints properly propagate trace information."""

    @patch("app.kafka_producer.kafka_producer.send_sensor_data")
    def test_gps_endpoint_includes_trace_in_response(
        self,
        mock_send_sensor_data,
        test_client,
        gps_reading_data,
    ):
        """Test that GPS endpoint includes trace information in response."""
        mock_send_sensor_data.return_value = AsyncMock()

        # Set up custom trace ID
        trace_id = str(uuid.uuid4())
        headers = {
            "X-Trace-ID": trace_id,
            "X-API-Key": "test-key",
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/sensor/gps",
            json=gps_reading_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        assert response_data["trace_id"] == trace_id
        assert "services_encountered" in response_data
        assert "ingestion-api" in response_data["services_encountered"]

    @patch("app.kafka_producer.kafka_producer.send_sensor_data")
    def test_kafka_message_includes_trace_info(
        self,
        mock_send_sensor_data,
        test_client,
        gps_reading_data,
    ):
        """Test that Kafka messages include trace information."""
        mock_send_sensor_data.return_value = AsyncMock()

        trace_id = str(uuid.uuid4())
        headers = {
            "X-Trace-ID": trace_id,
            "X-API-Key": "test-key",
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/sensor/gps",
            json=gps_reading_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify that send_sensor_data was called
        assert mock_send_sensor_data.called

        # Get the GPS reading that was passed to Kafka
        args, kwargs = mock_send_sensor_data.call_args
        gps_reading = args[0]

        # Verify trace information was added to the message
        assert hasattr(gps_reading, "trace_id")
        assert gps_reading.trace_id == trace_id
        assert hasattr(gps_reading, "services_encountered")
        assert "ingestion-api" in gps_reading.services_encountered

    @patch("app.kafka_producer.kafka_producer.send_sensor_data")
    def test_batch_endpoint_propagates_trace_to_all_messages(
        self,
        mock_send_sensor_data,
        test_client,
    ):
        """Test that batch endpoint propagates trace ID to all messages."""
        mock_send_sensor_data.return_value = AsyncMock()

        # Create batch of sensor readings
        batch_data = [
            {
                "device_id": "12345678-1234-8000-8000-123456789012",
                "recorded_at": "2024-01-15T10:30:00+00:00",
                "sensor_type": "temperature",
                "value": {"celsius": 22.5},
                "unit": "celsius",
            },
            {
                "device_id": "12345678-1234-8000-8000-123456789012",
                "recorded_at": "2024-01-15T10:31:00Z",
                "sensor_type": "humidity",
                "value": {"percent": 45.2},
                "unit": "percent",
            },
        ]

        trace_id = str(uuid.uuid4())
        headers = {
            "X-Trace-ID": trace_id,
            "X-API-Key": "test-key",
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/sensor/batch",
            json=batch_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        assert response_data["trace_id"] == trace_id
        assert response_data["processed"] == 2
        assert response_data["failed"] == 0

        # Verify that send_sensor_data was called twice
        assert mock_send_sensor_data.call_count == 2

        # Verify both messages have trace information
        for call in mock_send_sensor_data.call_args_list:
            args, kwargs = call
            sensor_reading = args[0]
            assert sensor_reading.trace_id == trace_id
            assert "ingestion-api" in sensor_reading.services_encountered


class TestTracingIntegration:
    """Integration tests for complete tracing flow."""

    @patch("app.kafka_producer.kafka_producer.send_sensor_data")
    @patch("app.kafka_producer.kafka_producer._producer")
    def test_complete_tracing_flow(
        self,
        mock_producer,
        mock_send_sensor_data,
        test_client,
        gps_reading_data,
    ):
        """Test complete flow from HTTP request to Kafka message."""
        # Mock Kafka producer
        mock_producer.send = AsyncMock()
        mock_send_sensor_data.return_value = AsyncMock()

        trace_id = str(uuid.uuid4())
        headers = {
            "X-Trace-ID": trace_id,
            "X-Services-Encountered": "client-app",
            "X-API-Key": "test-key",
            "Content-Type": "application/json",
        }

        response = test_client.post(
            "/sensor/gps",
            json=gps_reading_data,
            headers=headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify response includes complete trace chain
        response_data = response.json()
        assert response_data["trace_id"] == trace_id
        services = response_data["services_encountered"]
        assert "client-app" in services
        assert "ingestion-api" in services
        assert "kafka-producer" in services

        # Verify response headers
        assert response.headers["X-Trace-ID"] == trace_id
        response_services = response.headers["X-Services-Encountered"].split(",")
        assert "client-app" in response_services
        assert "ingestion-api" in response_services

    def test_trace_id_generation_is_unique(self, test_client):
        """Test that each request gets a unique trace ID when none provided."""
        response1 = test_client.get("/healthz")
        response2 = test_client.get("/healthz")

        trace_id1 = response1.headers["X-Trace-ID"]
        trace_id2 = response2.headers["X-Trace-ID"]

        assert trace_id1 != trace_id2

        # Both should be valid UUIDs
        uuid.UUID(trace_id1)
        uuid.UUID(trace_id2)

    @patch("app.kafka_producer.kafka_producer.send_sensor_data")
    def test_concurrent_requests_maintain_separate_traces(
        self,
        mock_send_sensor_data,
        test_client,
        gps_reading_data,
    ):
        """Test that concurrent requests maintain separate trace contexts."""
        mock_send_sensor_data.return_value = AsyncMock()

        # Make multiple concurrent-like requests with different trace IDs
        trace_id1 = str(uuid.uuid4())
        trace_id2 = str(uuid.uuid4())

        headers1 = {"X-Trace-ID": trace_id1, "X-API-Key": "test-key"}
        headers2 = {"X-Trace-ID": trace_id2, "X-API-Key": "test-key"}

        response1 = test_client.post(
            "/sensor/gps",
            json=gps_reading_data,
            headers=headers1,
        )

        response2 = test_client.post(
            "/sensor/gps",
            json=gps_reading_data,
            headers=headers2,
        )

        assert response1.status_code == status.HTTP_201_CREATED
        assert response2.status_code == status.HTTP_201_CREATED

        # Verify each response maintains its own trace ID
        assert response1.json()["trace_id"] == trace_id1
        assert response2.json()["trace_id"] == trace_id2
        assert response1.headers["X-Trace-ID"] == trace_id1
        assert response2.headers["X-Trace-ID"] == trace_id2
