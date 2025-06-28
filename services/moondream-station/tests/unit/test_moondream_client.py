"""Tests for Moondream client."""

import asyncio
import base64
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from PIL import Image

from app.config import settings
from app.models import (
    DetectedObject,
    ImageFeatures,
    MoondreamResponse,
    OCRBlock,
)
from app.moondream_client import MoondreamClient


@pytest.fixture
def moondream_client():
    """Create MoondreamClient instance."""
    return MoondreamClient()


@pytest.fixture
def sample_image():
    """Create sample image bytes."""
    image = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class TestMoondreamClient:
    """Test MoondreamClient functionality."""

    def test_init(self, moondream_client):
        """Test MoondreamClient initialization."""
        assert moondream_client.base_url == f"{settings.moondream_host}{settings.moondream_api_path}"
        assert moondream_client.timeout == settings.moondream_timeout
        assert moondream_client.max_retries == settings.moondream_max_retries

    @patch('app.moondream_client.httpx.AsyncClient')
    async def test_make_request_success(self, mock_client_class, moondream_client, mock_httpx_response):
        """Test successful HTTP request."""
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_httpx_response
        mock_client.get.return_value = mock_httpx_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await moondream_client._make_request("test", "POST", {"key": "value"})
        
        assert result == {"caption": "Test caption", "response": "Test response", "status": "ok"}
        mock_client.post.assert_called_once()

    @patch('app.moondream_client.httpx.AsyncClient')
    async def test_make_request_retry_on_503(self, mock_client_class, moondream_client):
        """Test retry on 503 error."""
        mock_client = AsyncMock()
        
        # First call returns 503, second succeeds
        mock_response_503 = Mock()
        mock_response_503.status_code = 503
        mock_response_503.raise_for_status.side_effect = Exception("503 Service Unavailable")
        
        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"status": "ok"}
        mock_response_ok.raise_for_status = Mock()
        
        mock_client.post.side_effect = [mock_response_503, mock_response_ok]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock asyncio.sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await moondream_client._make_request("test", "POST", {})
        
        assert result == {"status": "ok"}
        assert mock_client.post.call_count == 2

    @patch('app.moondream_client.httpx.AsyncClient')
    async def test_health_check_success(self, mock_client_class, moondream_client):
        """Test successful health check."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await moondream_client.health_check()
        
        assert result is True

    @patch('app.moondream_client.httpx.AsyncClient')
    async def test_health_check_failure(self, mock_client_class, moondream_client):
        """Test health check failure."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection error")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await moondream_client.health_check()
        
        assert result is False

    def test_prepare_image_no_resize(self, moondream_client, sample_image_base64):
        """Test image preparation without resizing."""
        image_bytes, mime_type = moondream_client._prepare_image(sample_image_base64)
        
        # Should return original size for small images
        original_image = Image.open(BytesIO(base64.b64decode(sample_image_base64)))
        prepared_image = Image.open(BytesIO(image_bytes))
        
        assert prepared_image.size == original_image.size
        assert mime_type in ["image/png", "image/jpeg"]

    def test_prepare_image_with_resize(self, moondream_client, sample_large_image_base64):
        """Test image preparation with resizing."""
        image_bytes, mime_type = moondream_client._prepare_image(sample_large_image_base64)
        
        # Should resize large images
        prepared_image = Image.open(BytesIO(image_bytes))
        
        assert prepared_image.width <= settings.max_image_size
        assert prepared_image.height <= settings.max_image_size
        assert mime_type in ["image/png", "image/jpeg"]

    @patch('app.moondream_client.MoondreamClient._make_request')
    async def test_caption_image(self, mock_request, moondream_client, sample_image_base64):
        """Test image captioning."""
        mock_request.return_value = {"caption": "A beautiful sunset"}
        
        result = await moondream_client.caption_image(sample_image_base64)
        
        assert result == "A beautiful sunset"
        mock_request.assert_called_once_with("caption", files=mock_request.call_args[1]["files"])

    @patch('app.moondream_client.MoondreamClient._make_request')
    async def test_query_image(self, mock_request, moondream_client, sample_image_base64):
        """Test image querying."""
        mock_request.return_value = {"response": "There are 3 cats in the image"}
        
        result = await moondream_client.query_image(
            sample_image_base64,
            "How many cats are in this image?"
        )
        
        assert result == "There are 3 cats in the image"
        
        # Verify request was made with query
        call_args = mock_request.call_args
        assert call_args[1]["data"]["query"] == "How many cats are in this image?"

    @patch('app.moondream_client.MoondreamClient.query_image')
    async def test_detect_objects(self, mock_query, moondream_client, sample_image_base64):
        """Test object detection."""
        mock_query.return_value = "I can see a person and a car in the image"
        
        objects = await moondream_client.detect_objects(sample_image_base64)
        
        assert len(objects) == 2
        assert objects[0].label == "person"
        assert objects[0].confidence == 0.85
        assert objects[1].label == "car"
        assert objects[1].confidence == 0.9

    @patch('app.moondream_client.MoondreamClient.query_image')
    async def test_extract_text(self, mock_query, moondream_client, sample_image_base64):
        """Test text extraction."""
        mock_query.return_value = "The sign says:\nWelcome\nOpen Daily\n9AM - 5PM"
        
        text_blocks = await moondream_client.extract_text(sample_image_base64)
        
        assert len(text_blocks) >= 1
        assert text_blocks[0].text == "The sign says:"
        assert text_blocks[0].confidence == 0.8

    @patch('app.moondream_client.MoondreamClient.query_image')
    async def test_analyze_visual_features(self, mock_query, moondream_client, sample_image_base64):
        """Test visual feature analysis."""
        mock_query.return_value = "The image is bright with high contrast and sharp details"
        
        features = await moondream_client.analyze_visual_features(sample_image_base64)
        
        assert isinstance(features, ImageFeatures)
        assert features.brightness == 0.8  # Based on "bright" in response
        assert features.sharpness == 0.9   # Based on "sharp" in response
        assert len(features.dominant_colors) > 0

    @patch('app.moondream_client.MoondreamClient.caption_image')
    @patch('app.moondream_client.MoondreamClient.query_image')
    @patch('app.moondream_client.MoondreamClient.detect_objects')
    @patch('app.moondream_client.MoondreamClient.extract_text')
    async def test_full_analysis(
        self,
        mock_extract,
        mock_detect,
        mock_query,
        mock_caption,
        moondream_client,
        sample_image_base64
    ):
        """Test full analysis."""
        mock_caption.return_value = "Test caption"
        mock_query.return_value = "Query response"
        mock_detect.return_value = [
            DetectedObject(label="test", confidence=0.9, bbox=[0, 0, 100, 100])
        ]
        mock_extract.return_value = [
            OCRBlock(text="Test text", confidence=0.95, bbox=[10, 10, 50, 50])
        ]
        
        result = await moondream_client.full_analysis(
            sample_image_base64,
            query="Test query",
            enable_objects=True,
            enable_ocr=True
        )
        
        assert isinstance(result, MoondreamResponse)
        assert result.caption == "Test caption"
        assert result.query_response == "Query response"
        assert len(result.objects) == 1
        assert len(result.text_blocks) == 1
        assert result.metadata["processing_time_ms"] > 0

    @patch('app.moondream_client.MoondreamClient._make_request')
    async def test_error_handling(self, mock_request, moondream_client, sample_image_base64):
        """Test error handling in API calls."""
        mock_request.side_effect = Exception("API Error")
        
        with pytest.raises(Exception, match="API Error"):
            await moondream_client.caption_image(sample_image_base64)

    def test_prepare_image_invalid_data(self, moondream_client):
        """Test image preparation with invalid data."""
        with pytest.raises(Exception):
            moondream_client._prepare_image("invalid_base64_data")

    @patch('app.moondream_client.MoondreamClient._make_request')
    async def test_timeout_handling(self, mock_request, moondream_client, sample_image_base64):
        """Test timeout handling."""
        mock_request.side_effect = asyncio.TimeoutError("Request timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await moondream_client.caption_image(sample_image_base64)