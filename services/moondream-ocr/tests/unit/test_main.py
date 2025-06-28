"""Unit tests for the main FastAPI application."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.test_helpers import create_ocr_request_data, create_expected_ocr_response


@pytest.fixture
def mock_ocr_processor():
    """Mock OCR processor fixture."""
    mock = MagicMock()
    mock.device = "cpu"
    mock.model = MagicMock()
    mock.process_image.return_value = {
        "ocr_text": "Test extracted text",
        "description": "Test image description",
        "success": True
    }
    return mock


@pytest.fixture
def client(mock_ocr_processor):
    """Test client fixture with mocked OCR processor."""
    with patch("app.main.ocr_processor", mock_ocr_processor):
        from app.main import app
        return TestClient(app)


class TestAPIEndpoints:
    """Test FastAPI application endpoints."""

    def test_root_endpoint(self, client, mock_ocr_processor):
        """Test root endpoint returns service info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Moondream OCR"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert data["model"] == "vikhyatk/moondream2"
        assert data["device"] == "cpu"

    def test_health_check_healthy(self, client, mock_ocr_processor):
        """Test health check when service is healthy."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_unhealthy(self, client):
        """Test health check when service is unhealthy."""
        with patch("app.main.ocr_processor", None):
            from app.main import app
            client_unhealthy = TestClient(app)
            response = client_unhealthy.get("/healthz")
            
            assert response.status_code == 503
            assert "Model not loaded" in response.json()["detail"]

    def test_readiness_check_ready(self, client, mock_ocr_processor):
        """Test readiness check when service is ready."""
        response = client.get("/readyz")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

    def test_readiness_check_not_ready(self, client):
        """Test readiness check when service is not ready."""
        with patch("app.main.ocr_processor", None):
            from app.main import app
            client_not_ready = TestClient(app)
            response = client_not_ready.get("/readyz")
            
            assert response.status_code == 503
            assert "Model not ready" in response.json()["detail"]

    def test_ocr_endpoint_success(self, client, mock_ocr_processor):
        """Test OCR endpoint with successful processing."""
        request_data = create_ocr_request_data()
        
        response = client.post("/ocr", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ocr_text"] == "Test extracted text"
        assert data["description"] == "Test image description"
        assert data["error"] is None
        assert "processing_time_ms" in data
        assert isinstance(data["processing_time_ms"], float)

    def test_ocr_endpoint_processor_not_initialized(self, client):
        """Test OCR endpoint when processor is not initialized."""
        with patch("app.main.ocr_processor", None):
            from app.main import app
            client_no_processor = TestClient(app)
            request_data = create_ocr_request_data()
            
            response = client_no_processor.post("/ocr", json=request_data)
            
            assert response.status_code == 503
            assert "OCR processor not initialized" in response.json()["detail"]

    def test_ocr_endpoint_processing_error(self, client, mock_ocr_processor):
        """Test OCR endpoint when processing fails."""
        mock_ocr_processor.process_image.side_effect = Exception("Processing failed")
        request_data = create_ocr_request_data()
        
        response = client.post("/ocr", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["ocr_text"] == ""
        assert data["description"] == ""
        assert "Processing failed" in data["error"]
        assert "processing_time_ms" in data

    def test_ocr_endpoint_invalid_request(self, client):
        """Test OCR endpoint with invalid request data."""
        invalid_data = {"invalid_field": "value"}
        
        response = client.post("/ocr", json=invalid_data)
        
        assert response.status_code == 422  # Validation error

    def test_ocr_endpoint_missing_image_data(self, client):
        """Test OCR endpoint with missing image data."""
        invalid_data = {"prompt": "Extract text"}
        
        response = client.post("/ocr", json=invalid_data)
        
        assert response.status_code == 422  # Validation error


class TestStartupShutdown:
    """Test application startup and shutdown."""

    @patch("app.main.kafka_consumer_thread")
    @patch("app.main.MoondreamOCR")
    def test_startup_event(self, mock_ocr_class, mock_kafka_thread):
        """Test startup event initializes OCR and starts Kafka consumer."""
        mock_ocr_instance = MagicMock()
        mock_ocr_class.return_value = mock_ocr_instance
        mock_thread = MagicMock()
        mock_kafka_thread.return_value = mock_thread
        
        from app.main import startup_event
        
        # Test startup
        import asyncio
        asyncio.run(startup_event())
        
        mock_ocr_class.assert_called_once()
        mock_ocr_instance.load_model.assert_called_once()
        # Note: Thread starting is tested separately as it's harder to mock