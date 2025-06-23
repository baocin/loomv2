"""Test main FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka consumer."""
    with patch('app.main.kafka_consumer') as mock:
        mock.start = AsyncMock()
        mock.stop = AsyncMock()
        mock.running = True
        mock.asr_processor.model = "mocked"
        yield mock


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, client, mock_kafka_consumer):
        """Test /healthz endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "parakeet-tdt"
    
    def test_readiness_endpoint(self, client, mock_kafka_consumer):
        """Test /readyz endpoint."""
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert data["checks"]["service"] == "parakeet-tdt"
    
    def test_readiness_not_ready(self, client, mock_kafka_consumer):
        """Test readiness when service is not ready."""
        mock_kafka_consumer.running = False
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False


class TestMetricsEndpoint:
    """Test metrics endpoint."""
    
    def test_metrics_endpoint(self, client, mock_kafka_consumer):
        """Test /metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert b"parakeet_audio_chunks_processed_total" in response.content
        assert b"parakeet_transcripts_produced_total" in response.content


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_endpoint(self, client, mock_kafka_consumer):
        """Test / endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "parakeet-tdt"
        assert data["version"] == "1.0.0"
        assert "environment" in data
        assert "model" in data
        assert "device" in data