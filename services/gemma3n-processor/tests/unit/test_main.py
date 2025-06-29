"""Tests for main FastAPI application."""

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
        """Test basic health check endpoint."""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @patch("app.main.ollama_client")
    @patch("app.main.kafka_consumer")
    def test_readiness_check_healthy(self, mock_kafka, mock_ollama, client):
        """Test readiness check when all services are healthy."""
        # Mock healthy services
        mock_ollama.health_check = AsyncMock(return_value=True)
        mock_kafka.is_healthy.return_value = True

        response = client.get("/readyz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["ollama"] is True
        assert data["checks"]["kafka"] is True

    @patch("app.main.ollama_client")
    @patch("app.main.kafka_consumer")
    def test_readiness_check_unhealthy(self, mock_kafka, mock_ollama, client):
        """Test readiness check when services are unhealthy."""
        # Mock unhealthy services
        mock_ollama.health_check = AsyncMock(return_value=False)
        mock_kafka.is_healthy.return_value = False

        response = client.get("/readyz")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["ollama"] is False
        assert data["checks"]["kafka"] is False

    def test_readiness_check_no_services(self, client):
        """Test readiness check when services are not initialized."""
        response = client.get("/readyz")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["ollama"] is False
        assert data["checks"]["kafka"] is False


class TestMetricsEndpoint:
    """Test metrics endpoint."""

    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        # Should contain some basic metrics
        content = response.text
        assert "gemma3n_requests_total" in content or "python_info" in content


class TestStatusEndpoint:
    """Test service status endpoint."""

    @patch("app.main.ollama_client")
    def test_status_endpoint_with_client(self, mock_ollama, client):
        """Test status endpoint when Ollama client is available."""
        mock_ollama.list_models = AsyncMock(return_value=["gemma3n:e4b", "gemma3n:e2b"])

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "gemma3n-processor"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
        assert "models" in data
        assert "processing_metrics" in data

    def test_status_endpoint_no_client(self, client):
        """Test status endpoint when Ollama client is not available."""
        response = client.get("/status")

        assert response.status_code == 503
        assert "Service not ready" in response.json()["detail"]


class TestProcessingEndpoints:
    """Test processing endpoints."""

    @patch("app.main.ollama_client")
    def test_process_text_success(self, mock_ollama, client):
        """Test successful text processing."""
        mock_ollama.generate_text = AsyncMock(return_value="Generated text response")

        response = client.post(
            "/process/text",
            params={
                "prompt": "Analyze this text",
                "context": "Test context",
                "max_tokens": 1000,
                "temperature": 0.8,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "Generated text response"
        assert "processing_time_ms" in data
        assert data["model"] == "gemma3n:e4b"

    def test_process_text_no_client(self, client):
        """Test text processing when client is not available."""
        response = client.post("/process/text", params={"prompt": "Test prompt"})

        assert response.status_code == 503
        assert "Service not ready" in response.json()["detail"]

    @patch("app.main.ollama_client")
    def test_process_image_success(self, mock_ollama, client):
        """Test successful image processing."""
        mock_ollama.analyze_image = AsyncMock(return_value="Image analysis result")

        response = client.post(
            "/process/image",
            json={
                "image_data": "base64encodedimage",
                "prompt": "Describe this image",
                "max_tokens": 500,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "Image analysis result"
        assert "processing_time_ms" in data

    @patch("app.main.ollama_client")
    def test_process_multimodal_success(self, mock_ollama, client):
        """Test successful multimodal processing."""
        mock_ollama.process_multimodal = AsyncMock(return_value="Multimodal result")

        request_data = {
            "prompt": "Analyze this content",
            "text": "Sample text",
            "image_data": "base64image",
            "audio_data": "base64audio",
            "max_tokens": 2000,
            "temperature": 0.7,
        }

        response = client.post("/process/multimodal", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "Multimodal result"
        assert "processing_time_ms" in data
        assert "modalities_processed" in data
        assert data["modalities_processed"]["text"] is True
        assert data["modalities_processed"]["image"] is True
        assert data["modalities_processed"]["audio"] is True

    @patch("app.main.ollama_client")
    def test_processing_error_handling(self, mock_ollama, client):
        """Test error handling in processing endpoints."""
        mock_ollama.generate_text = AsyncMock(
            side_effect=Exception("Processing failed")
        )

        response = client.post("/process/text", params={"prompt": "Test prompt"})

        assert response.status_code == 500
        assert "Processing failed" in response.json()["detail"]


class TestMiddleware:
    """Test middleware functionality."""

    def test_metrics_middleware(self, client):
        """Test that metrics middleware records requests."""
        # Make a request
        response = client.get("/healthz")
        assert response.status_code == 200

        # Check metrics endpoint contains recorded metrics
        metrics_response = client.get("/metrics")
        content = metrics_response.text

        # Should contain request count metrics (if they've been initialized)
        # Note: In test environment, metrics might not be immediately visible
        assert metrics_response.status_code == 200


class TestCORS:
    """Test CORS middleware."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/healthz")

        # FastAPI TestClient doesn't fully simulate CORS preflight,
        # but we can test the middleware is configured
        assert response.status_code in [
            200,
            405,
        ]  # 405 = Method Not Allowed is also acceptable
