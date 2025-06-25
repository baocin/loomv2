"""Performance and load tests for Silero VAD."""

import asyncio
import base64
import os
import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import numpy as np
import psutil
import pytest

from app.models import AudioChunk
from app.vad_processor import VADProcessor


class TestPerformance:
    """Performance and load tests for VAD service."""

    @pytest.fixture
    def vad_processor(self):
        """Create a real VAD processor for performance testing."""
        # For performance tests, we might want to use a real model
        # but with mocked torch.hub.load to avoid download
        with patch("app.vad_processor.torch.hub.load") as mock_load:
            mock_model = MagicMock()

            # Simulate realistic processing time
            def mock_inference(audio_tensor):
                time.sleep(0.01)  # 10ms processing time
                return torch.tensor([[0.8]])

            mock_model.side_effect = mock_inference
            mock_load.return_value = (mock_model, None)

            processor = VADProcessor(threshold=0.5)
            return processor

    def create_audio_chunk(self, duration_seconds=1.0, sample_rate=16000):
        """Create a realistic audio chunk."""
        num_samples = int(sample_rate * duration_seconds)
        # Create realistic speech-like audio (mix of frequencies)
        t = np.linspace(0, duration_seconds, num_samples)
        audio = (
            0.3 * np.sin(2 * np.pi * 200 * t)
            + 0.2 * np.sin(2 * np.pi * 800 * t)  # Low frequency
            + 0.1 * np.sin(2 * np.pi * 2000 * t)  # Mid frequency
            + 0.1 * np.random.randn(num_samples)  # High frequency  # Noise
        ).astype(np.float32)

        audio_bytes = audio.tobytes()

        return AudioChunk(
            device_id="perf-test-device",
            recorded_at=datetime.now(UTC).isoformat(),
            data=base64.b64encode(audio_bytes).decode(),
            sample_rate=sample_rate,
            channels=1,
            duration_ms=int(duration_seconds * 1000),
        )

    async def test_single_message_latency(self, vad_processor):
        """Test processing latency for a single message."""
        chunk = self.create_audio_chunk(duration_seconds=1.0)

        # Measure processing time
        start_time = time.perf_counter()
        result = await vad_processor.process_audio(chunk)
        end_time = time.perf_counter()

        processing_time = end_time - start_time

        # Processing should be fast (< 100ms for 1 second of audio)
        assert processing_time < 0.1, f"Processing took {processing_time:.3f}s"

        # Log performance metric
        print(f"Single message latency: {processing_time * 1000:.2f}ms")

    async def test_throughput(self, vad_processor):
        """Test messages per second throughput."""
        num_messages = 100
        chunks = [
            self.create_audio_chunk(duration_seconds=0.5) for _ in range(num_messages)
        ]

        # Process all messages and measure time
        start_time = time.perf_counter()

        tasks = [vad_processor.process_audio(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        throughput = num_messages / total_time

        print(f"Throughput: {throughput:.2f} messages/second")
        print(f"Total time for {num_messages} messages: {total_time:.2f}s")

        # Should handle at least 10 messages per second
        assert throughput > 10, f"Throughput too low: {throughput:.2f} msg/s"

    async def test_memory_usage(self, vad_processor):
        """Test memory usage during extended processing."""
        process = psutil.Process(os.getpid())

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process many messages
        for i in range(500):
            chunk = self.create_audio_chunk(duration_seconds=0.5)
            await vad_processor.process_audio(chunk)

            # Check memory every 100 messages
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                print(
                    f"After {i} messages: Memory increased by {memory_increase:.2f}MB"
                )

        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory

        print(f"Total memory increase: {total_increase:.2f}MB")

        # Memory increase should be reasonable (< 100MB)
        assert (
            total_increase < 100
        ), f"Memory leak detected: {total_increase:.2f}MB increase"

    async def test_concurrent_processing(self, vad_processor):
        """Test concurrent processing performance."""
        num_concurrent = 20
        chunks = [
            self.create_audio_chunk(duration_seconds=1.0) for _ in range(num_concurrent)
        ]

        # Measure concurrent processing
        start_time = time.perf_counter()

        tasks = [vad_processor.process_audio(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_message = total_time / num_concurrent

        print(f"Concurrent processing ({num_concurrent} messages):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time per message: {avg_time_per_message * 1000:.2f}ms")

        # Concurrent processing should be efficient
        # Should be much less than sequential time
        expected_sequential_time = num_concurrent * 0.01  # 10ms per message
        assert total_time < expected_sequential_time * 0.5  # At least 2x speedup

    async def test_varying_audio_lengths(self, vad_processor):
        """Test performance with different audio lengths."""
        durations = [0.1, 0.5, 1.0, 2.0, 5.0]  # seconds

        for duration in durations:
            chunk = self.create_audio_chunk(duration_seconds=duration)

            start_time = time.perf_counter()
            result = await vad_processor.process_audio(chunk)
            end_time = time.perf_counter()

            processing_time = end_time - start_time
            processing_ratio = processing_time / duration

            print(
                f"Audio duration: {duration}s, Processing time: {processing_time * 1000:.2f}ms"
            )
            print(f"  Processing ratio: {processing_ratio:.3f} (lower is better)")

            # Processing should be much faster than real-time
            assert processing_ratio < 0.1  # Should process 10x faster than real-time

    async def test_stress_test(self, vad_processor):
        """Stress test with high load."""
        # Simulate 1 minute of continuous high-load processing
        test_duration = 60  # seconds
        message_interval = 0.1  # 10 messages per second

        start_time = time.time()
        messages_processed = 0
        errors = 0

        while time.time() - start_time < test_duration:
            try:
                chunk = self.create_audio_chunk(duration_seconds=0.5)
                result = await vad_processor.process_audio(chunk)
                messages_processed += 1
            except Exception as e:
                errors += 1
                print(f"Error during stress test: {e}")

            await asyncio.sleep(message_interval)

        total_time = time.time() - start_time
        success_rate = (messages_processed - errors) / messages_processed * 100

        print("Stress test results:")
        print(f"  Duration: {total_time:.1f}s")
        print(f"  Messages processed: {messages_processed}")
        print(f"  Errors: {errors}")
        print(f"  Success rate: {success_rate:.1f}%")

        # Should maintain high success rate under stress
        assert success_rate > 99.0, f"Too many errors: {errors}/{messages_processed}"

    async def test_cpu_usage(self, vad_processor):
        """Monitor CPU usage during processing."""
        process = psutil.Process(os.getpid())

        # Get baseline CPU
        process.cpu_percent()  # First call to initialize
        await asyncio.sleep(1)
        baseline_cpu = process.cpu_percent()

        # Process messages continuously for 10 seconds
        start_time = time.time()
        cpu_samples = []

        while time.time() - start_time < 10:
            chunk = self.create_audio_chunk(duration_seconds=0.5)
            await vad_processor.process_audio(chunk)

            # Sample CPU usage
            cpu_usage = process.cpu_percent()
            cpu_samples.append(cpu_usage)

            await asyncio.sleep(0.1)

        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)

        print("CPU usage during processing:")
        print(f"  Baseline: {baseline_cpu:.1f}%")
        print(f"  Average: {avg_cpu:.1f}%")
        print(f"  Maximum: {max_cpu:.1f}%")

        # CPU usage should be reasonable
        assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"

    @pytest.mark.parametrize("sample_rate", [8000, 16000, 44100, 48000])
    async def test_resampling_performance(self, vad_processor, sample_rate):
        """Test performance impact of different sample rates."""
        chunk = self.create_audio_chunk(duration_seconds=1.0, sample_rate=sample_rate)

        # Measure processing time
        start_time = time.perf_counter()
        result = await vad_processor.process_audio(chunk)
        end_time = time.perf_counter()

        processing_time = end_time - start_time

        print(f"Sample rate {sample_rate}Hz: {processing_time * 1000:.2f}ms")

        # All sample rates should be processed efficiently
        assert processing_time < 0.2  # 200ms max

    async def test_model_warmup(self, vad_processor):
        """Test model warmup effect on performance."""
        # First few inferences might be slower
        warmup_times = []

        for i in range(10):
            chunk = self.create_audio_chunk(duration_seconds=0.5)

            start_time = time.perf_counter()
            await vad_processor.process_audio(chunk)
            end_time = time.perf_counter()

            warmup_times.append(end_time - start_time)

        # Check if performance improves after warmup
        first_half_avg = sum(warmup_times[:5]) / 5
        second_half_avg = sum(warmup_times[5:]) / 5

        print("Warmup performance:")
        print(f"  First 5 calls: {first_half_avg * 1000:.2f}ms avg")
        print(f"  Next 5 calls: {second_half_avg * 1000:.2f}ms avg")

        # Second half should be faster or similar (warmed up)
        assert second_half_avg <= first_half_avg * 1.1  # Allow 10% variance


# Add missing import
import torch
