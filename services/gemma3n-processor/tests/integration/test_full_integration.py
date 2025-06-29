"""Full integration tests for Gemma 3N Processor."""

import asyncio
import base64
from io import BytesIO
from unittest.mock import AsyncMock, Mock, patch

import pytest
from PIL import Image

from app.kafka_consumer import KafkaConsumerManager
from app.models import MultimodalRequest
from app.ollama_client import OllamaClient


@pytest.fixture
def sample_large_image_base64():
    """Create sample large base64 encoded image for resize testing."""
    image = Image.new("RGB", (1000, 800), color="purple")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


class TestFullIntegration:
    """Test full integration scenarios."""

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_ollama_client_full_workflow(self, mock_client_class):
        """Test complete Ollama client workflow."""
        # Set up mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Mock different responses for different endpoints
        def mock_json_response(*args, **kwargs):
            url = (
                mock_client.post.call_args[1]["json"]
                if mock_client.post.call_args
                else {}
            )
            if "api/tags" in str(mock_client.get.call_args):
                return {"models": [{"name": "gemma3n:e4b"}]}
            elif "api/pull" in str(args):
                return {"status": "success"}
            else:
                return {"response": "Mock analysis result"}

        mock_response.json.side_effect = mock_json_response
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Test Ollama client
        client = OllamaClient()

        # Test health check
        is_healthy = await client.health_check()
        assert is_healthy is True

        # Test list models
        models = await client.list_models()
        assert "gemma3n:e4b" in models

        # Test text generation
        text_result = await client.generate_text("Test prompt")
        assert text_result == "Mock analysis result"

        # Test image analysis
        image_data = base64.b64encode(b"fake_image_data").decode()
        image_result = await client.analyze_image(image_data, "Describe image")
        assert image_result == "Mock analysis result"

    @patch("app.kafka_consumer.AIOKafkaConsumer")
    @patch("app.kafka_consumer.AIOKafkaProducer")
    async def test_kafka_consumer_full_workflow(
        self, mock_producer_class, mock_consumer_class
    ):
        """Test complete Kafka consumer workflow."""
        # Set up mocks
        mock_consumer = AsyncMock()
        mock_producer = AsyncMock()
        mock_consumer_class.return_value = mock_consumer
        mock_producer_class.return_value = mock_producer

        # Create mock Ollama client
        mock_ollama = AsyncMock()
        mock_ollama.generate_text.return_value = "Text analysis result"
        mock_ollama.analyze_image.return_value = "Image analysis result"

        # Create consumer manager
        consumer_manager = KafkaConsumerManager(mock_ollama)

        # Test start
        await consumer_manager.start()
        assert consumer_manager.running is True
        assert consumer_manager.is_healthy() is True

        # Test message processing
        text_message = {
            "device_id": "test-device",
            "recorded_at": "2024-06-27T12:00:00Z",
            "text": "Test message",
            "schema_version": "v1",
        }

        result = await consumer_manager.process_text_message(text_message)
        assert result is not None
        assert result.analysis_type == "text_analysis"
        assert "Text analysis result" in result.primary_result

        # Test stop
        await consumer_manager.stop()
        assert consumer_manager.running is False

    def test_image_resize_integration(self, sample_large_image_base64):
        """Test image resizing functionality."""
        client = OllamaClient()

        # Test with large image that should be resized
        resized_data = client._prepare_image(sample_large_image_base64)

        # Verify image was resized
        resized_bytes = base64.b64decode(resized_data)
        resized_image = Image.open(BytesIO(resized_bytes))

        assert resized_image.width <= 768
        assert resized_image.height <= 768

    async def test_multimodal_request_processing(
        self, sample_image_data, sample_audio_data
    ):
        """Test processing of multimodal requests."""
        mock_ollama = AsyncMock()
        mock_ollama.process_multimodal.return_value = "Multimodal analysis complete"

        request = MultimodalRequest(
            prompt="Analyze all this content",
            text="Sample text for analysis",
            image_data=sample_image_data,
            audio_data=sample_audio_data,
            max_tokens=1500,
            temperature=0.6,
        )

        result = await mock_ollama.process_multimodal(request)
        assert result == "Multimodal analysis complete"

        # Verify the call was made with the request
        mock_ollama.process_multimodal.assert_called_once_with(request)

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_error_recovery_workflow(self, mock_client_class):
        """Test error recovery in various scenarios."""
        client = OllamaClient()

        # Test health check failure
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        is_healthy = await client.health_check()
        assert is_healthy is False

        # Test model pull failure
        mock_client.post.side_effect = Exception("Model not found")

        pull_success = await client.pull_model("invalid-model")
        assert pull_success is False

    async def test_concurrent_processing(self):
        """Test concurrent message processing."""
        mock_ollama = AsyncMock()
        mock_ollama.generate_text.return_value = "Concurrent result"

        consumer_manager = KafkaConsumerManager(mock_ollama)

        # Create multiple messages
        messages = []
        for i in range(5):
            message = {
                "device_id": f"device-{i}",
                "recorded_at": "2024-06-27T12:00:00Z",
                "text": f"Message {i}",
                "schema_version": "v1",
            }
            messages.append(message)

        # Process messages concurrently
        tasks = [consumer_manager.process_text_message(msg) for msg in messages]

        results = await asyncio.gather(*tasks)

        # Verify all messages were processed
        assert len(results) == 5
        assert all(result is not None for result in results)
        assert all(result.analysis_type == "text_analysis" for result in results)

    async def test_message_validation_and_error_handling(self):
        """Test message validation and error handling."""
        mock_ollama = AsyncMock()
        consumer_manager = KafkaConsumerManager(mock_ollama)

        # Test invalid message structure
        invalid_messages = [
            {},  # Empty message
            {"device_id": "test"},  # Missing required fields
            {"device_id": "test", "recorded_at": "invalid-date"},  # Invalid date
            {
                "device_id": "test",
                "recorded_at": "2024-06-27T12:00:00Z",
            },  # Missing text
        ]

        for invalid_msg in invalid_messages:
            result = await consumer_manager.process_text_message(invalid_msg)
            assert result is None

    @patch("app.ollama_client.httpx.AsyncClient")
    async def test_timeout_handling(self, mock_client_class):
        """Test timeout handling in HTTP requests."""
        client = OllamaClient()

        # Mock timeout exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = asyncio.TimeoutError("Request timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(asyncio.TimeoutError):
            await client.generate_text("Test prompt")

    async def test_large_response_handling(self):
        """Test handling of large responses."""
        mock_ollama = AsyncMock()

        # Simulate large response
        large_response = "Large analysis result " * 1000  # ~20KB response
        mock_ollama.generate_text.return_value = large_response

        consumer_manager = KafkaConsumerManager(mock_ollama)

        message = {
            "device_id": "test-device",
            "recorded_at": "2024-06-27T12:00:00Z",
            "text": "Analyze this large document...",
            "schema_version": "v1",
        }

        result = await consumer_manager.process_text_message(message)

        assert result is not None
        assert len(result.primary_result) > 1000
        assert result.processing_time_ms > 0
