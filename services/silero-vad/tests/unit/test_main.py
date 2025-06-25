"""Unit tests for main application."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test liveness probe."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "silero-vad"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"

    @patch("app.main.consumer")
    def test_readiness_check_not_ready(self, mock_consumer, client):
        """Test readiness when consumer not running."""
        mock_consumer._running = False
        response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json()["status"] == "not ready"

    @patch("app.main.consumer")
    async def test_readiness_check_healthy(self, mock_consumer, client):
        """Test readiness when healthy."""
        mock_consumer._running = True
        mock_consumer.health_check = AsyncMock(return_value={"status": "healthy"})
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @patch("app.main.consumer")
    async def test_metrics_endpoint(self, mock_consumer, client):
        """Test metrics endpoint."""
        mock_consumer.health_check = AsyncMock(
            return_value={
                "status": "healthy",
                "consumer_running": True,
                "active_tasks": 2,
            }
        )
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "silero-vad"
        assert data["environment"] == "development"
        assert "consumer" in data
