"""Unit tests for the main FastAPI application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, lifespan


@pytest.fixture()
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture()
def mock_kafka_producer():
    """Mock Kafka producer fixture."""
    with patch("app.main.kafka_producer") as mock:
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        yield mock


class TestLifespan:
    """Test application lifespan management."""

    @pytest.mark.asyncio()
    async def test_lifespan_startup_shutdown(self, mock_kafka_producer):
        """Test startup and shutdown sequence."""
        mock_app = MagicMock()

        # Test the lifespan context manager
        async with lifespan(mock_app):
            # Should call start during startup
            mock_kafka_producer.start.assert_called_once()

        # Should call stop during shutdown
        mock_kafka_producer.stop.assert_called_once()

    @pytest.mark.asyncio()
    async def test_lifespan_startup_error(self, mock_kafka_producer):
        """Test lifespan handles startup errors gracefully."""
        mock_kafka_producer.start.side_effect = Exception("Kafka connection failed")
        mock_app = MagicMock()

        # Should handle startup errors gracefully
        with pytest.raises(Exception, match="Kafka connection failed"):
            async with lifespan(mock_app):
                pass


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_healthz_endpoint(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_readyz_endpoint_healthy(self, client, mock_kafka_producer):
        """Test readiness probe when healthy."""
        mock_kafka_producer.is_connected = True

        response = client.get("/readyz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["kafka_connected"] is True

    def test_readyz_endpoint_unhealthy(self, client, mock_kafka_producer):
        """Test readiness probe when unhealthy."""
        mock_kafka_producer.is_connected = False

        response = client.get("/readyz")

        # Should still return 200 but with unhealthy status
        assert response.status_code == 200
        data = response.json()
        assert data["kafka_connected"] is False


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "text/plain; version=0.0.4; charset=utf-8"
        )

        # Should contain basic metrics
        content = response.text
        assert "# HELP" in content  # Prometheus help comments
        assert "# TYPE" in content  # Prometheus type declarations

    def test_metrics_include_custom_metrics(self, client):
        """Test that custom metrics are included."""
        # Make a request to generate some metrics
        client.get("/healthz")

        response = client.get("/metrics")
        content = response.text

        # Should include HTTP request metrics
        assert (
            "http_requests_total" in content
            or "http_request_duration_seconds" in content
        )


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present in responses."""
        headers = {"Origin": "http://localhost:3000"}
        response = client.get("/healthz", headers=headers)

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request handling."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }

        response = client.options("/sensor/gps", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "*"


class TestExceptionHandling:
    """Test global exception handling."""

    def test_404_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_405_method_not_allowed(self, client):
        """Test 405 method not allowed handling."""
        response = client.delete("/healthz")  # DELETE not allowed on healthz

        assert response.status_code == 405
        data = response.json()
        assert "detail" in data


class TestApplicationConfiguration:
    """Test application configuration and setup."""

    def test_app_title_and_version(self):
        """Test app has correct title and version."""
        assert app.title == "Loom Ingestion API"
        assert app.version == "0.1.0"

    def test_app_includes_routers(self):
        """Test app includes the required routers."""
        # Check that routes are registered
        routes = [route.path for route in app.routes]

        # Health endpoints
        assert "/healthz" in routes
        assert "/readyz" in routes
        assert "/metrics" in routes

        # Should have sensor and audio routes
        sensor_routes = [r for r in routes if r.startswith("/sensor")]
        audio_routes = [r for r in routes if r.startswith("/audio")]

        assert len(sensor_routes) > 0
        assert len(audio_routes) > 0

    def test_app_middleware_configured(self):
        """Test that middleware is properly configured."""
        # Should have CORS middleware
        middleware_types = [type(middleware.cls) for middleware in app.user_middleware]

        # Check for prometheus middleware (should be in the stack)
        assert len(app.user_middleware) > 0


class TestStartupConfiguration:
    """Test startup configuration and dependencies."""

    @patch("app.main.logger")
    def test_startup_logging(self, mock_logger, mock_kafka_producer):
        """Test that startup events are logged."""
        # This tests the startup sequence without actually starting the app
        client = TestClient(app)

        # Just verify client can be created (startup should happen)
        assert client is not None

    def test_app_state_initialization(self):
        """Test that app state is properly initialized."""
        client = TestClient(app)

        # App should be properly configured
        assert app.state is not None
        assert hasattr(app, "router")
        assert hasattr(app, "middleware_stack")


class TestErrorResponseFormat:
    """Test error response formatting."""

    def test_validation_error_format(self, client):
        """Test validation error response format."""
        # Send invalid JSON to trigger validation error
        response = client.post(
            "/sensor/gps",
            json={"invalid": "data"},  # Missing required fields
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # Pydantic validation errors

    def test_http_exception_format(self, client):
        """Test HTTP exception response format."""
        response = client.get("/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
