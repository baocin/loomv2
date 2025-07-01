#!/usr/bin/env python3
"""Test script for VAD pipeline - sends test audio to Kafka and monitors results."""

import asyncio
import json
import base64
import numpy as np
from datetime import datetime
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import argparse


async def generate_test_audio(duration_seconds=5, sample_rate=16000):
    """Generate test audio with speech-like patterns."""
    import struct
    import io
    
    # Create audio with alternating silence and "speech" (sine waves)
    samples = int(duration_seconds * sample_rate)
    audio = np.zeros(samples, dtype=np.int16)

    # Add some "speech" segments with more realistic patterns
    speech_segments = [
        (0.5, 1.5),  # 1 second of speech starting at 0.5s
        (2.0, 3.5),  # 1.5 seconds of speech starting at 2s
        (4.0, 4.8),  # 0.8 seconds of speech starting at 4s
    ]

    for start, end in speech_segments:
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        t = np.arange(end_sample - start_sample) / sample_rate
        
        # Create more complex waveform that resembles speech
        # Mix multiple frequencies to simulate formants
        signal = np.zeros_like(t)
        
        # Add fundamental frequency (100-200 Hz for speech)
        f0 = 120 + np.random.randint(-20, 20)
        signal += np.sin(2 * np.pi * f0 * t) * 0.3
        
        # Add formants (characteristic frequencies of speech)
        # F1: 700-1220 Hz
        f1 = 800 + np.random.randint(-100, 100)
        signal += np.sin(2 * np.pi * f1 * t) * 0.2
        
        # F2: 1220-2600 Hz  
        f2 = 1800 + np.random.randint(-200, 200)
        signal += np.sin(2 * np.pi * f2 * t) * 0.15
        
        # F3: 2600-3200 Hz
        f3 = 2800 + np.random.randint(-200, 200)
        signal += np.sin(2 * np.pi * f3 * t) * 0.1
        
        # Add some amplitude modulation to simulate speech rhythm
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)  # 4 Hz modulation
        signal *= envelope
        
        # Add slight noise
        signal += np.random.normal(0, 0.02, len(t))
        
        # Scale to int16 range
        signal *= 25000
        audio[start_sample:end_sample] = signal.astype(np.int16)

    # Create WAV file in memory
    wav_io = io.BytesIO()
    
    # WAV header
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = len(audio) * 2  # 2 bytes per sample for int16
    
    # Write RIFF header
    wav_io.write(b'RIFF')
    wav_io.write(struct.pack('<I', 36 + data_size))  # File size - 8
    wav_io.write(b'WAVE')
    
    # Write fmt chunk
    wav_io.write(b'fmt ')
    wav_io.write(struct.pack('<I', 16))  # Subchunk size
    wav_io.write(struct.pack('<H', 1))   # Audio format (PCM)
    wav_io.write(struct.pack('<H', num_channels))
    wav_io.write(struct.pack('<I', sample_rate))
    wav_io.write(struct.pack('<I', byte_rate))
    wav_io.write(struct.pack('<H', block_align))
    wav_io.write(struct.pack('<H', bits_per_sample))
    
    # Write data chunk
    wav_io.write(b'data')
    wav_io.write(struct.pack('<I', data_size))
    wav_io.write(audio.tobytes())
    
    return wav_io.getvalue()


async def send_test_audio(bootstrap_servers="localhost:9092"):
    """Send test audio to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )

    await producer.start()

    try:
        # Generate test audio
        audio_bytes = await generate_test_audio()

        # Create audio chunk message with nested data structure
        message = {
            "device_id": "test-device-001",
            "timestamp": datetime.utcnow().isoformat(),
            "schema_version": "v1",
            "trace_id": f"test-{datetime.utcnow().timestamp()}",
            "data": {
                "audio_data": base64.b64encode(audio_bytes).decode("utf-8"),
                "format": "pcm",
                "sample_rate": 16000,
                "channels": 1,
                "bits_per_sample": 16,
                "duration_ms": 5000,
                "device_info": {"microphone": "Test Microphone", "gain": 0.8},
            },
            "metadata": {"test": True, "source": "test_vad_pipeline"},
        }

        # Send to Kafka
        await producer.send_and_wait(
            "device.audio.raw", value=message, key=b"test-device-001"
        )

        print("✅ Sent test audio chunk to Kafka")
        print(f"   Device ID: {message['device_id']}")
        print(f"   Duration: {message['data']['duration_ms']}ms")
        print(f"   Timestamp: {message['timestamp']}")

    finally:
        await producer.stop()


async def monitor_vad_results(bootstrap_servers="localhost:9092", timeout=30):
    """Monitor VAD results from Kafka."""
    consumer = AIOKafkaConsumer(
        "media.audio.vad_filtered",
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",  # Changed to earliest to see all messages
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    await consumer.start()

    try:
        print(f"\n📡 Monitoring VAD results (timeout: {timeout}s)...")

        results = []
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # Poll for messages with timeout
                msg = await asyncio.wait_for(
                    consumer.getone(),
                    timeout=min(
                        5, timeout - (asyncio.get_event_loop().time() - start_time)
                    ),
                )

                result = msg.value
                results.append(result)

                print("\n🎤 Speech segment detected:")
                print(f"   Device ID: {result['device_id']}")
                print(f"   VAD Confidence: {result.get('vad_confidence', 'N/A')}")
                print(f"   Speech Probability: {result.get('speech_probability', 'N/A')}")  
                print(f"   Duration: {result.get('duration_ms', 'N/A')}ms")
                print(f"   Sample Rate: {result.get('sample_rate', 'N/A')} Hz")
                print(f"   Chunk Index: {result.get('chunk_index', 'N/A')}")

            except asyncio.TimeoutError:
                continue

        print("\n📊 Summary:")
        print(f"   Total segments found: {len(results)}")

        if results:
            total_speech_ms = sum(r.get("duration_ms", 0) for r in results)
            print(f"   Total speech duration: {total_speech_ms}ms")
            confidences = [r.get("vad_confidence", 0) for r in results if "vad_confidence" in r]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                print(f"   Average confidence: {avg_confidence:.2f}")

    finally:
        await consumer.stop()


async def main():
    parser = argparse.ArgumentParser(description="Test VAD pipeline")
    parser.add_argument(
        "--bootstrap-servers", default="localhost:9092", help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--send-only",
        action="store_true",
        help="Only send test audio, don't monitor results",
    )
    parser.add_argument(
        "--monitor-only",
        action="store_true",
        help="Only monitor results, don't send test audio",
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Monitoring timeout in seconds"
    )

    args = parser.parse_args()

    print("🔊 VAD Pipeline Test")
    print("===================")

    if not args.monitor_only:
        await send_test_audio(args.bootstrap_servers)
        if not args.send_only:
            await asyncio.sleep(2)  # Give VAD processor time to start

    if not args.send_only:
        await monitor_vad_results(args.bootstrap_servers, args.timeout)


if __name__ == "__main__":
    asyncio.run(main())
