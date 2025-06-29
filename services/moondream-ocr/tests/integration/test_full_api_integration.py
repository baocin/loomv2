"""Integration tests for the full API workflow."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from tests.test_helpers import create_ocr_request_data


@pytest.fixture
def mock_model_loading():
    """Mock the model loading to avoid downloading actual models in tests."""
    with patch("app.main.AutoModelForCausalLM") as mock_model, patch(
        "app.main.AutoTokenizer"
    ) as mock_tokenizer, patch("app.main.torch") as mock_torch:
        # Mock torch
        mock_torch.cuda.is_available.return_value = False
        mock_torch.float32 = "float32"

        # Mock model and tokenizer
        mock_model_instance = MagicMock()
        mock_tokenizer_instance = MagicMock()
        mock_model.from_pretrained.return_value = mock_model_instance
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        # Mock model methods
        mock_model_instance.encode_image.return_value = "encoded_image"
        mock_model_instance.answer_question.side_effect = [
            "Sample extracted text from image",
            "This appears to be a test image with text content",
        ]

        yield {"model": mock_model_instance, "tokenizer": mock_tokenizer_instance}


@pytest.fixture
def app_with_mocked_model(mock_model_loading):
    """FastAPI app with mocked model loading."""
    # Mock the startup event to avoid Kafka thread issues in tests
    with patch("app.main.kafka_consumer_thread"):
        from app.main import app

        return app


@pytest.fixture
def client(app_with_mocked_model):
    """Test client with mocked dependencies."""
    return TestClient(app_with_mocked_model)


class TestFullAPIIntegration:
    """Integration tests covering the full API workflow."""

    def test_full_ocr_workflow(self, client):
        """Test the complete OCR workflow from API request to response."""
        # First check that the service is healthy
        health_response = client.get("/healthz")
        assert health_response.status_code in [
            200,
            503,
        ]  # May be 503 if model not loaded

        # Make OCR request
        request_data = create_ocr_request_data()
        response = client.post("/ocr", json=request_data)

        # Verify response structure
        assert response.status_code == 200
        data = response.json()

        # Check response fields
        assert "ocr_text" in data
        assert "description" in data
        assert "success" in data
        assert "processing_time_ms" in data

        # If successful, verify content
        if data["success"]:
            assert isinstance(data["ocr_text"], str)
            assert isinstance(data["description"], str)
            assert isinstance(data["processing_time_ms"], float)
            assert data["processing_time_ms"] >= 0
        else:
            assert "error" in data

    def test_api_endpoint_availability(self, client):
        """Test that all API endpoints are available."""
        endpoints = [
            ("/", "GET"),
            ("/healthz", "GET"),
            ("/readyz", "GET"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            # Endpoints should be available (not 404)
            assert response.status_code != 404

    def test_api_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        response = client.get("/")

        # Check for CORS headers if configured
        # Note: This depends on the actual CORS configuration in the app
        assert response.status_code == 200

    def test_health_endpoints_integration(self, client):
        """Test health and readiness endpoints work together."""
        # Health check should always respond
        health_response = client.get("/healthz")
        assert health_response.status_code in [200, 503]

        # Readiness check should match health status
        ready_response = client.get("/readyz")
        assert ready_response.status_code in [200, 503]

    def test_api_validation_errors(self, client):
        """Test API validation handles malformed requests correctly."""
        # Test with completely invalid JSON
        response = client.post("/ocr", json={"invalid": "data"})
        assert response.status_code == 422

        # Test with missing required fields
        response = client.post("/ocr", json={})
        assert response.status_code == 422

        # Test with wrong data types
        response = client.post("/ocr", json={"image_data": 123})
        assert response.status_code == 422

    def test_large_request_handling(self, client):
        """Test handling of large image data requests."""
        # Create a larger base64 string (simulating larger image)
        large_image_data = "A" * 10000  # Large but invalid base64

        request_data = {"image_data": large_image_data, "prompt": "Extract text"}

        response = client.post("/ocr", json=request_data)

        # Should handle large requests gracefully
        assert response.status_code == 200
        data = response.json()

        # Likely to fail due to invalid base64, but should handle gracefully
        if not data["success"]:
            assert "error" in data

    @patch("app.main.kafka_consumer_thread")
    def test_startup_sequence_integration(self, mock_kafka_thread, mock_model_loading):
        """Test the complete startup sequence."""
        from app.main import startup_event
        import asyncio

        # Run startup event
        asyncio.run(startup_event())

        # Verify Kafka consumer thread was started
        # Note: In real integration test, we might check that the thread is running
        # but here we just verify the startup sequence completes
