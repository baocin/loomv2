"""Integration tests for Silero VAD with Kafka."""

import asyncio
import base64
import json
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.kafka_consumer import KafkaConsumerService
from app.models import AudioChunk, VADFilteredAudio


class TestKafkaIntegration:
    """Test Kafka integration for VAD service."""

    @pytest.fixture
    async def mock_kafka_consumer(self):
        """Mock AIOKafkaConsumer."""
        consumer = AsyncMock()
        consumer.start = AsyncMock()
        consumer.stop = AsyncMock()
        consumer.subscribe = AsyncMock()
        consumer.commit = AsyncMock()
        return consumer

    @pytest.fixture
    async def mock_kafka_producer(self):
        """Mock Kafka producer."""
        producer = AsyncMock()
        producer.send_message = AsyncMock()
        producer._is_connected = True
        return producer

    @pytest.fixture
    async def mock_vad_processor(self):
        """Mock VAD processor."""
        processor = AsyncMock()
        processor.process_audio = AsyncMock()
        return processor

    @pytest.fixture
    async def kafka_consumer_service(self, mock_kafka_producer, mock_vad_processor):
        """Create Kafka consumer service with mocks."""
        with patch("app.kafka_consumer.settings") as mock_settings:
            mock_settings.kafka_bootstrap_servers = "localhost:9092"
            mock_settings.kafka_consumer_group = "test-group"
            mock_settings.input_topic = "device.audio.raw"
            mock_settings.output_topic = "media.audio.vad_filtered"
            
            service = KafkaConsumerService(mock_kafka_producer)
            service.vad_processor = mock_vad_processor
            return service

    def create_kafka_message(self, audio_chunk):
        """Create a mock Kafka message."""
        message = MagicMock()
        message.value = json.dumps(audio_chunk.model_dump()).encode()
        message.topic = "device.audio.raw"
        message.partition = 0
        message.offset = 100
        return message

    async def test_process_valid_message(self, kafka_consumer_service, mock_kafka_producer):
        """Test processing a valid audio message."""
        # Create test audio
        audio = np.random.randn(16000).astype(np.float32) * 0.3
        audio_bytes = audio.tobytes()
        
        chunk = AudioChunk(
            device_id="test-device-123",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            data=base64.b64encode(audio_bytes).decode(),
            sample_rate=16000,
            channels=1,
            duration_ms=1000
        )
        
        message = self.create_kafka_message(chunk)
        
        # Mock VAD detection
        filtered = VADFilteredAudio(
            device_id=chunk.device_id,
            recorded_at=chunk.recorded_at,
            data=chunk.data,
            sample_rate=chunk.sample_rate,
            channels=chunk.channels,
            duration_ms=chunk.duration_ms,
            speech_probability=0.85,
            start_time=0.0,
            end_time=1.0
        )
        
        kafka_consumer_service.vad_processor.process_audio.return_value = filtered
        
        # Process message
        await kafka_consumer_service._process_message(message)
        
        # Verify VAD was called
        kafka_consumer_service.vad_processor.process_audio.assert_called_once()
        
        # Verify message was sent to output topic
        mock_kafka_producer.send_message.assert_called_once()
        call_args = mock_kafka_producer.send_message.call_args
        assert call_args[0][0] == "media.audio.vad_filtered"
        assert isinstance(call_args[0][1], VADFilteredAudio)

    async def test_process_no_speech_detected(self, kafka_consumer_service, mock_kafka_producer):
        """Test when no speech is detected."""
        # Create silent audio
        audio = np.zeros(16000, dtype=np.float32)
        audio_bytes = audio.tobytes()
        
        chunk = AudioChunk(
            device_id="test-device-456",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            data=base64.b64encode(audio_bytes).decode(),
            sample_rate=16000,
            channels=1,
            duration_ms=1000
        )
        
        message = self.create_kafka_message(chunk)
        
        # Mock no speech detected
        kafka_consumer_service.vad_processor.process_audio.return_value = None
        
        # Process message
        await kafka_consumer_service._process_message(message)
        
        # Verify VAD was called
        kafka_consumer_service.vad_processor.process_audio.assert_called_once()
        
        # Verify no message was sent (no speech)
        mock_kafka_producer.send_message.assert_not_called()

    async def test_process_invalid_json(self, kafka_consumer_service):
        """Test processing invalid JSON message."""
        message = MagicMock()
        message.value = b"invalid json {["
        message.topic = "device.audio.raw"
        
        # Should handle gracefully
        await kafka_consumer_service._process_message(message)
        
        # VAD should not be called
        kafka_consumer_service.vad_processor.process_audio.assert_not_called()

    async def test_process_missing_fields(self, kafka_consumer_service):
        """Test processing message with missing required fields."""
        # Missing device_id
        invalid_chunk = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "data": "somedata",
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 1000
        }
        
        message = MagicMock()
        message.value = json.dumps(invalid_chunk).encode()
        message.topic = "device.audio.raw"
        
        # Should handle validation error
        await kafka_consumer_service._process_message(message)
        
        # VAD should not be called
        kafka_consumer_service.vad_processor.process_audio.assert_not_called()

    async def test_concurrent_message_processing(self, kafka_consumer_service, mock_kafka_producer):
        """Test processing multiple messages concurrently."""
        # Create multiple messages
        messages = []
        for i in range(10):
            audio = np.random.randn(8000).astype(np.float32) * 0.3
            chunk = AudioChunk(
                device_id=f"device-{i}",
                recorded_at=datetime.now(timezone.utc).isoformat(),
                data=base64.b64encode(audio.tobytes()).decode(),
                sample_rate=16000,
                channels=1,
                duration_ms=500
            )
            messages.append(self.create_kafka_message(chunk))
        
        # Mock VAD to return speech for half the messages
        async def mock_process(chunk):
            device_num = int(chunk.device_id.split('-')[1])
            if device_num % 2 == 0:
                return VADFilteredAudio(
                    device_id=chunk.device_id,
                    recorded_at=chunk.recorded_at,
                    data=chunk.data,
                    sample_rate=chunk.sample_rate,
                    channels=chunk.channels,
                    duration_ms=chunk.duration_ms,
                    speech_probability=0.8,
                    start_time=0.0,
                    end_time=0.5
                )
            return None
            
        kafka_consumer_service.vad_processor.process_audio.side_effect = mock_process
        
        # Process all messages concurrently
        tasks = [kafka_consumer_service._process_message(msg) for msg in messages]
        await asyncio.gather(*tasks)
        
        # Should have processed all messages
        assert kafka_consumer_service.vad_processor.process_audio.call_count == 10
        
        # Should have sent 5 messages (speech detected in half)
        assert mock_kafka_producer.send_message.call_count == 5

    async def test_vad_processor_exception(self, kafka_consumer_service):
        """Test handling VAD processor exceptions."""
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            data=base64.b64encode(b"audio").decode(),
            sample_rate=16000,
            channels=1,
            duration_ms=1000
        )
        
        message = self.create_kafka_message(chunk)
        
        # Mock VAD processor to raise exception
        kafka_consumer_service.vad_processor.process_audio.side_effect = Exception("VAD error")
        
        # Should handle exception gracefully
        await kafka_consumer_service._process_message(message)
        
        # Should have attempted processing
        kafka_consumer_service.vad_processor.process_audio.assert_called_once()

    async def test_kafka_producer_error(self, kafka_consumer_service, mock_kafka_producer):
        """Test handling Kafka producer errors."""
        chunk = AudioChunk(
            device_id="test-device",
            recorded_at=datetime.now(timezone.utc).isoformat(),
            data=base64.b64encode(b"audio").decode(),
            sample_rate=16000,
            channels=1,
            duration_ms=1000
        )
        
        message = self.create_kafka_message(chunk)
        
        # Mock successful VAD
        filtered = VADFilteredAudio(
            device_id=chunk.device_id,
            recorded_at=chunk.recorded_at,
            data=chunk.data,
            sample_rate=chunk.sample_rate,
            channels=chunk.channels,
            duration_ms=chunk.duration_ms,
            speech_probability=0.9,
            start_time=0.0,
            end_time=1.0
        )
        
        kafka_consumer_service.vad_processor.process_audio.return_value = filtered
        
        # Mock producer error
        mock_kafka_producer.send_message.side_effect = Exception("Kafka send error")
        
        # Should handle error gracefully
        await kafka_consumer_service._process_message(message)
        
        # Should have attempted to send
        mock_kafka_producer.send_message.assert_called_once()

    async def test_message_ordering(self, kafka_consumer_service, mock_kafka_producer):
        """Test that messages from same device maintain order."""
        device_id = "test-device-order"
        messages = []
        
        # Create sequence of messages from same device
        for i in range(5):
            audio = np.random.randn(4000).astype(np.float32) * 0.3
            chunk = AudioChunk(
                device_id=device_id,
                recorded_at=f"2024-01-01T00:00:{i:02d}Z",  # Sequential timestamps
                data=base64.b64encode(audio.tobytes()).decode(),
                sample_rate=16000,
                channels=1,
                duration_ms=250,
                timestamp=f"2024-01-01T00:00:{i:02d}Z"  # Server timestamp
            )
            messages.append(self.create_kafka_message(chunk))
        
        # Mock VAD to always detect speech
        async def mock_process(chunk):
            return VADFilteredAudio(
                device_id=chunk.device_id,
                recorded_at=chunk.recorded_at,
                data=chunk.data,
                sample_rate=chunk.sample_rate,
                channels=chunk.channels,
                duration_ms=chunk.duration_ms,
                speech_probability=0.8,
                start_time=0.0,
                end_time=0.25
            )
            
        kafka_consumer_service.vad_processor.process_audio.side_effect = mock_process
        
        # Process messages in order
        for msg in messages:
            await kafka_consumer_service._process_message(msg)
        
        # Verify all messages were processed in order
        assert mock_kafka_producer.send_message.call_count == 5
        
        # Check timestamps are in order
        calls = mock_kafka_producer.send_message.call_args_list
        timestamps = [call[0][1].recorded_at for call in calls]
        assert timestamps == sorted(timestamps)  # Should be in chronological order