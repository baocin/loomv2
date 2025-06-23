"""Unit tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_healthz(self, client):
        """Test liveness probe endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_readyz_not_ready(self, client):
        """Test readiness probe when not ready."""
        with patch("app.main.app_ready", False):
            response = client.get("/readyz")
            assert response.status_code == 503
            data = response.json()
            assert data["detail"]["status"] == "not_ready"

    def test_readyz_ready(self, client):
        """Test readiness probe when ready."""
        with patch("app.main.app_ready", True), \
             patch("app.main.kafka_consumer_task", AsyncMock(done=lambda: False)):
            response = client.get("/readyz")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["checks"]["app_initialized"] is True


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        assert b"minicpm_vision_requests_total" in response.content


class TestRootEndpoints:
    """Test root endpoints."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "minicpm-vision"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert "model" in data
        assert "input_topics" in data
        assert "output_topic" in data

    def test_status(self, client):
        """Test status endpoint."""
        with patch("app.main.app_ready", True), \
             patch("app.main.kafka_consumer_task", AsyncMock(done=lambda: False)):
            response = client.get("/status")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "minicpm-vision"
            assert data["ready"] is True
            assert "kafka_consumer" in data
            assert "configuration" in data