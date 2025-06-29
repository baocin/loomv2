"""Tests for Ollama client."""

import base64
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from PIL import Image

from app.config import settings
from app.models import MultimodalRequest
from app.ollama_client import OllamaClient


@pytest.fixture
def ollama_client():
    """Create OllamaClient instance."""
    return OllamaClient()


@pytest.fixture
def mock_httpx_client():
    """Create mock httpx client."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "test response"}
    mock_response.raise_for_status = Mock()
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_image_base64():
    """Create sample base64 encoded image."""
    image = Image.new("RGB", (100, 100), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


class TestOllamaClient:
    """Test OllamaClient functionality."""

    def test_init(self, ollama_client):
        """Test OllamaClient initialization."""
        assert ollama_client.base_url == settings.ollama_host
        assert ollama_client.model == settings.ollama_model
        assert ollama_client.timeout == settings.ollama_timeout
        assert ollama_client.keep_alive == settings.ollama_keep_alive

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_make_request_success(
        self, mock_client_class, ollama_client, mock_httpx_client
    ):
        """Test successful HTTP request."""
        mock_client_class.return_value.__aenter__.return_value = mock_httpx_client

        result = await ollama_client._make_request("api/test", {"key": "value"})

        assert result == {"response": "test response"}
        mock_httpx_client.post.assert_called_once()

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_make_request_http_error(self, mock_client_class, ollama_client):
        """Test HTTP error handling."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(Exception):
            await ollama_client._make_request("api/test", {})

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_health_check_success(
        self, mock_client_class, ollama_client, mock_httpx_client
    ):
        """Test successful health check."""
        mock_client_class.return_value.__aenter__.return_value = mock_httpx_client

        result = await ollama_client.health_check()

        assert result is True
        mock_httpx_client.get.assert_called_once_with(
            f"{settings.ollama_host}/api/tags"
        )

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_health_check_failure(self, mock_client_class, ollama_client):
        """Test health check failure."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        result = await ollama_client.health_check()

        assert result is False

    @patch("app.ollama_client.OllamaClient._make_request")
    async def test_list_models(self, mock_request, ollama_client):
        """Test listing models."""
        mock_request.return_value = {
            "models": [{"name": "gemma3n:e2b"}, {"name": "gemma3n:e4b"}]
        }

        models = await ollama_client.list_models()

        assert models == ["gemma3n:e2b", "gemma3n:e4b"]
        mock_request.assert_called_once_with("api/tags", {})

    @patch("app.ollama_client.OllamaClient._make_request")
    async def test_pull_model_success(self, mock_request, ollama_client):
        """Test successful model pull."""
        mock_request.return_value = {}

        result = await ollama_client.pull_model("gemma3n:e4b")

        assert result is True
        mock_request.assert_called_once_with("api/pull", {"name": "gemma3n:e4b"})

    @patch("app.ollama_client.OllamaClient._make_request")
    async def test_pull_model_failure(self, mock_request, ollama_client):
        """Test model pull failure."""
        mock_request.side_effect = Exception("Pull failed")

        result = await ollama_client.pull_model("gemma3n:e4b")

        assert result is False

    def test_prepare_image_no_resize(self, ollama_client, sample_image_base64):
        """Test image preparation without resizing."""
        result = ollama_client._prepare_image(sample_image_base64)

        # Should return the same data for small images
        assert result == sample_image_base64

    def test_prepare_image_with_resize(self, ollama_client):
        """Test image preparation with resizing."""
        # Create large image that needs resizing
        large_image = Image.new("RGB", (1000, 1000), color="green")
        buffer = BytesIO()
        large_image.save(buffer, format="PNG")
        large_base64 = base64.b64encode(buffer.getvalue()).decode()

        result = ollama_client._prepare_image(large_base64)

        # Should return different data after resizing
        assert result != large_base64

        # Verify resized image is within limits
        resized_bytes = base64.b64decode(result)
        resized_image = Image.open(BytesIO(resized_bytes))
        assert resized_image.width <= settings.max_image_size
        assert resized_image.height <= settings.max_image_size

    @patch("app.ollama_client.OllamaClient._make_request")
    async def test_generate_text(self, mock_request, ollama_client):
        """Test text generation."""
        mock_request.return_value = {"response": "Generated text response"}

        result = await ollama_client.generate_text(
            prompt="Test prompt",
            context="Test context",
            max_tokens=1000,
            temperature=0.8,
        )

        assert result == "Generated text response"

        # Verify request was made with correct parameters
        call_args = mock_request.call_args
        assert call_args[0][0] == "api/generate"

        request_data = call_args[0][1]
        assert request_data["model"] == settings.ollama_model
        assert "Test context\nTest prompt" in request_data["prompt"]
        assert request_data["options"]["num_predict"] == 1000
        assert request_data["options"]["temperature"] == 0.8

    @patch("app.ollama_client.OllamaClient._make_request")
    @patch("app.ollama_client.OllamaClient._prepare_image")
    async def test_analyze_image(
        self, mock_prepare, mock_request, ollama_client, sample_image_base64
    ):
        """Test image analysis."""
        mock_prepare.return_value = sample_image_base64
        mock_request.return_value = {"response": "Image analysis result"}

        result = await ollama_client.analyze_image(
            image_data=sample_image_base64,
            prompt="Describe this image",
            max_tokens=500,
            temperature=0.5,
        )

        assert result == "Image analysis result"
        mock_prepare.assert_called_once_with(sample_image_base64)

        # Verify request parameters
        call_args = mock_request.call_args
        request_data = call_args[0][1]
        assert request_data["model"] == settings.ollama_model
        assert request_data["prompt"] == "Describe this image"
        assert request_data["images"] == [sample_image_base64]
        assert request_data["options"]["num_predict"] == 500
        assert request_data["options"]["temperature"] == 0.5

    @patch("app.ollama_client.OllamaClient._make_request")
    @patch("app.ollama_client.OllamaClient._prepare_image")
    async def test_process_multimodal(
        self, mock_prepare, mock_request, ollama_client, sample_image_base64
    ):
        """Test multimodal processing."""
        mock_prepare.return_value = sample_image_base64
        mock_request.return_value = {"response": "Multimodal analysis result"}

        request = MultimodalRequest(
            prompt="Analyze this content",
            text="Sample text",
            image_data=sample_image_base64,
            audio_data="base64audio",
            max_tokens=2000,
            temperature=0.7,
        )

        result = await ollama_client.process_multimodal(request)

        assert result == "Multimodal analysis result"
        mock_prepare.assert_called_once_with(sample_image_base64)

        # Verify request contains all modalities
        call_args = mock_request.call_args
        request_data = call_args[0][1]
        assert "Sample text" in request_data["prompt"]
        assert "Image provided for analysis" in request_data["prompt"]
        assert "Audio data provided for analysis" in request_data["prompt"]
        assert request_data["images"] == [sample_image_base64]

    @patch("app.ollama_client.OllamaClient._make_request")
    async def test_process_multimodal_text_only(self, mock_request, ollama_client):
        """Test multimodal processing with text only."""
        mock_request.return_value = {"response": "Text only result"}

        request = MultimodalRequest(
            prompt="Analyze this text", text="Sample text content"
        )

        result = await ollama_client.process_multimodal(request)

        assert result == "Text only result"

        # Verify no images in request
        call_args = mock_request.call_args
        request_data = call_args[0][1]
        assert "images" not in request_data
        assert "Sample text content" in request_data["prompt"]
