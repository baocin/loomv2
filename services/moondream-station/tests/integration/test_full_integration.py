"""Full integration tests for Moondream Station service."""

import asyncio
import base64
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.kafka_consumer import KafkaConsumerManager
from app.models import (
    ImageFeatures,
    MoondreamAnalysisResult,
)
from app.moondream_client import MoondreamClient


class TestFullIntegration:
    """Test full integration scenarios."""

    @patch("app.moondream_client.httpx.AsyncClient")
    async def test_moondream_client_workflow(self, mock_client_class):
        """Test complete Moondream client workflow."""
        # Set up mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Mock different responses
        def mock_json_response():
            url = str(mock_client.post.call_args)
            if "caption" in url:
                return {"caption": "A scenic mountain view"}
            elif "query" in url:
                return {"response": "I can see mountains and a lake"}
            else:
                return {"status": "ok"}

        mock_response.json.side_effect = mock_json_response
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Test client
        client = MoondreamClient()

        # Test health check
        is_healthy = await client.health_check()
        assert is_healthy is True

        # Test image captioning
        test_image = base64.b64encode(b"fake_image_data").decode()
        caption = await client.caption_image(test_image)
        assert "mountain" in caption.lower()

        # Test image query
        query_response = await client.query_image(test_image, "What do you see?")
        assert "mountains" in query_response.lower()

    async def test_kafka_consumer_workflow(self):
        """Test complete Kafka consumer workflow."""
        # Create mock Moondream client
        mock_moondream = AsyncMock()
        mock_moondream.full_analysis.return_value = Mock(
            caption="Test caption",
            query_response="Test response",
            objects=[{"label": "test", "confidence": 0.9, "bbox": [0, 0, 100, 100]}],
            text_blocks=[{"text": "test", "confidence": 0.9, "bbox": [0, 0, 50, 50]}],
            metadata={"processing_time_ms": 100},
        )
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#FF0000"],
            brightness=0.7,
            contrast=0.6,
            sharpness=0.8,
            aspect_ratio=1.5,
        )

        # Create consumer manager
        consumer_manager = KafkaConsumerManager(mock_moondream)

        # Test message processing
        image_message = {
            "device_id": "test-device",
            "recorded_at": datetime.utcnow().isoformat(),
            "data": base64.b64encode(b"test_image_data").decode(),
            "format": "jpeg",
            "metadata": {"location": "test"},
        }

        result = await consumer_manager.process_image_message(
            image_message, "device.image.camera.raw"
        )

        assert result is not None
        assert isinstance(result, MoondreamAnalysisResult)
        assert result.device_id == "test-device"
        assert result.caption == "Test caption"
        assert len(result.detected_objects) == 1
        assert len(result.ocr_blocks) == 1

    async def test_error_recovery_workflow(self):
        """Test error recovery in various scenarios."""
        mock_moondream = AsyncMock()

        # Simulate failure then success
        mock_moondream.full_analysis.side_effect = [
            Exception("First attempt failed"),
            Mock(
                caption="Success on retry",
                query_response=None,
                objects=[],
                text_blocks=[],
                metadata={},
            ),
        ]
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#000000"],
            brightness=0.5,
            contrast=0.5,
            sharpness=0.5,
            aspect_ratio=1.0,
        )

        consumer_manager = KafkaConsumerManager(mock_moondream)

        # First attempt should fail
        message = {
            "device_id": "test-device",
            "recorded_at": datetime.utcnow().isoformat(),
            "data": base64.b64encode(b"test").decode(),
        }

        result1 = await consumer_manager.process_image_message(message, "test.topic")
        assert result1.error is not None
        assert "First attempt failed" in result1.error

        # Second attempt should succeed
        result2 = await consumer_manager.process_image_message(message, "test.topic")
        assert result2.error is None
        assert result2.caption == "Success on retry"

    async def test_concurrent_processing(self):
        """Test concurrent message processing."""
        mock_moondream = AsyncMock()
        mock_moondream.full_analysis.return_value = Mock(
            caption="Concurrent result",
            query_response=None,
            objects=[],
            text_blocks=[],
            metadata={"processing_time_ms": 50},
        )
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#FFFFFF"],
            brightness=0.8,
            contrast=0.7,
            sharpness=0.9,
            aspect_ratio=1.33,
        )

        consumer_manager = KafkaConsumerManager(mock_moondream)

        # Create multiple messages
        messages = []
        for i in range(5):
            message = {
                "device_id": f"device-{i}",
                "recorded_at": datetime.utcnow().isoformat(),
                "data": base64.b64encode(f"image-{i}".encode()).decode(),
                "format": "png",
            }
            messages.append(message)

        # Process messages concurrently
        tasks = [
            consumer_manager.process_image_message(msg, "test.topic")
            for msg in messages
        ]

        results = await asyncio.gather(*tasks)

        # Verify all messages were processed
        assert len(results) == 5
        assert all(result is not None for result in results)
        assert all(result.caption == "Concurrent result" for result in results)
        assert all(f"device-{i}" == results[i].device_id for i in range(5))

    async def test_different_topic_processing(self):
        """Test processing messages from different topics."""
        mock_moondream = AsyncMock()
        mock_moondream.full_analysis.return_value = Mock(
            caption="Topic-specific processing",
            query_response="Query answer",
            objects=[],
            text_blocks=[],
            metadata={},
        )
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#123456"],
            brightness=0.6,
            contrast=0.5,
            sharpness=0.7,
            aspect_ratio=1.0,
        )

        consumer_manager = KafkaConsumerManager(mock_moondream)

        # Test different topics
        topics = [
            "device.image.camera.raw",
            "device.video.screen.raw",
            "task.image.analyze",
        ]

        for topic in topics:
            message = {
                "device_id": "test-device",
                "recorded_at": datetime.utcnow().isoformat(),
                "data": base64.b64encode(b"test").decode(),
                "metadata": {"query": "What is this?"} if "task" in topic else None,
            }

            result = await consumer_manager.process_image_message(message, topic)

            assert result is not None
            assert result.caption == "Topic-specific processing"

            # Task topic should have query response
            if "task" in topic:
                assert result.query_response == "Query answer"

    async def test_scene_detection(self):
        """Test scene type and attribute detection."""
        mock_moondream = AsyncMock()

        # Test different scene types
        scenes = [
            ("An indoor office space with computers", "indoor", ["technology"]),
            ("Outdoor landscape with mountains", "outdoor", ["nature"]),
            ("Portrait of a person smiling", "portrait", ["people"]),
            ("Urban street with cars and buildings", None, ["urban"]),
        ]

        consumer_manager = KafkaConsumerManager(mock_moondream)

        for caption, expected_type, expected_attrs in scenes:
            mock_moondream.full_analysis.return_value = Mock(
                caption=caption,
                query_response=None,
                objects=[],
                text_blocks=[],
                metadata={},
            )
            mock_moondream.analyze_visual_features.return_value = ImageFeatures(
                dominant_colors=["#AABBCC"],
                brightness=0.7,
                contrast=0.6,
                sharpness=0.8,
                aspect_ratio=1.5,
            )

            message = {
                "device_id": "test-device",
                "recorded_at": datetime.utcnow().isoformat(),
                "data": base64.b64encode(b"test").decode(),
            }

            result = await consumer_manager.process_image_message(message, "test.topic")

            assert result.scene_type == expected_type
            if expected_attrs:
                assert any(attr in result.scene_attributes for attr in expected_attrs)

    async def test_object_counting(self):
        """Test object counting functionality."""
        mock_moondream = AsyncMock()
        mock_moondream.full_analysis.return_value = Mock(
            caption="Multiple objects",
            query_response=None,
            objects=[
                {"label": "person", "confidence": 0.9, "bbox": [0, 0, 100, 100]},
                {"label": "person", "confidence": 0.85, "bbox": [100, 0, 200, 100]},
                {"label": "car", "confidence": 0.95, "bbox": [200, 0, 300, 100]},
                {"label": "person", "confidence": 0.8, "bbox": [300, 0, 400, 100]},
            ],
            text_blocks=[],
            metadata={},
        )
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#FFFFFF"],
            brightness=0.7,
            contrast=0.6,
            sharpness=0.8,
            aspect_ratio=1.0,
        )

        consumer_manager = KafkaConsumerManager(mock_moondream)

        message = {
            "device_id": "test-device",
            "recorded_at": datetime.utcnow().isoformat(),
            "data": base64.b64encode(b"test").decode(),
        }

        result = await consumer_manager.process_image_message(message, "test.topic")

        assert result.object_count == {"person": 3, "car": 1}
        assert len(result.detected_objects) == 4

    async def test_ocr_text_concatenation(self):
        """Test OCR text block concatenation."""
        mock_moondream = AsyncMock()
        mock_moondream.full_analysis.return_value = Mock(
            caption="Text in image",
            query_response=None,
            objects=[],
            text_blocks=[
                {"text": "Hello", "confidence": 0.95, "bbox": [0, 0, 50, 20]},
                {"text": "World", "confidence": 0.93, "bbox": [60, 0, 110, 20]},
                {"text": "Test", "confidence": 0.91, "bbox": [0, 30, 50, 50]},
            ],
            metadata={},
        )
        mock_moondream.analyze_visual_features.return_value = ImageFeatures(
            dominant_colors=["#000000"],
            brightness=0.5,
            contrast=0.7,
            sharpness=0.9,
            aspect_ratio=1.0,
        )

        consumer_manager = KafkaConsumerManager(mock_moondream)

        message = {
            "device_id": "test-device",
            "recorded_at": datetime.utcnow().isoformat(),
            "data": base64.b64encode(b"test").decode(),
        }

        result = await consumer_manager.process_image_message(message, "test.topic")

        assert len(result.ocr_blocks) == 3
        assert result.full_text == "Hello World Test"
