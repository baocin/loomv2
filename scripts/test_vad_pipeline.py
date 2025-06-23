#!/usr/bin/env python3
"""Test script for VAD pipeline - sends test audio to Kafka and monitors results."""

import asyncio
import json
import base64
import numpy as np
from datetime import datetime
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import argparse
import sys


async def generate_test_audio(duration_seconds=5, sample_rate=16000):
    """Generate test audio with speech-like patterns."""
    # Create audio with alternating silence and "speech" (sine waves)
    samples = int(duration_seconds * sample_rate)
    audio = np.zeros(samples, dtype=np.int16)
    
    # Add some "speech" segments
    speech_segments = [
        (0.5, 1.5),   # 1 second of speech starting at 0.5s
        (2.0, 3.5),   # 1.5 seconds of speech starting at 2s
        (4.0, 4.8),   # 0.8 seconds of speech starting at 4s
    ]
    
    for start, end in speech_segments:
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        # Generate sine wave to simulate speech
        t = np.arange(end_sample - start_sample) / sample_rate
        frequency = 440 + np.random.randint(-100, 100)  # Vary frequency
        segment = np.sin(2 * np.pi * frequency * t) * 16000
        audio[start_sample:end_sample] = segment.astype(np.int16)
    
    return audio.tobytes()


async def send_test_audio(bootstrap_servers="localhost:9092"):
    """Send test audio to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
    )
    
    await producer.start()
    
    try:
        # Generate test audio
        audio_bytes = await generate_test_audio()
        
        # Create audio chunk message
        message = {
            "device_id": "test-device-001",
            "timestamp": datetime.utcnow().isoformat(),
            "schema_version": "v1",
            "chunk_number": 1,
            "audio_data": base64.b64encode(audio_bytes).decode('utf-8'),
            "format": "pcm16",
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 5000,
            "metadata": {"test": True, "source": "test_vad_pipeline"}
        }
        
        # Send to Kafka
        await producer.send_and_wait(
            "device.audio.raw",
            value=message,
            key=b"test-device-001"
        )
        
        print(f"✅ Sent test audio chunk to Kafka")
        print(f"   Device ID: {message['device_id']}")
        print(f"   Duration: {message['duration_ms']}ms")
        print(f"   Timestamp: {message['timestamp']}")
        
    finally:
        await producer.stop()


async def monitor_vad_results(bootstrap_servers="localhost:9092", timeout=30):
    """Monitor VAD results from Kafka."""
    consumer = AIOKafkaConsumer(
        "media.audio.vad_filtered",
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='latest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
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
                    timeout=min(5, timeout - (asyncio.get_event_loop().time() - start_time))
                )
                
                result = msg.value
                results.append(result)
                
                print(f"\n🎤 Speech segment detected:")
                print(f"   Device ID: {result['device_id']}")
                print(f"   Confidence: {result['confidence']:.2f}")
                print(f"   Start: {result['segment_start_ms']}ms")
                print(f"   Duration: {result['segment_duration_ms']}ms")
                print(f"   Model: {result['processing_model']} v{result['processing_version']}")
                
            except asyncio.TimeoutError:
                continue
        
        print(f"\n📊 Summary:")
        print(f"   Total segments found: {len(results)}")
        
        if results:
            total_speech_ms = sum(r['segment_duration_ms'] for r in results)
            print(f"   Total speech duration: {total_speech_ms}ms")
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            print(f"   Average confidence: {avg_confidence:.2f}")
        
    finally:
        await consumer.stop()


async def main():
    parser = argparse.ArgumentParser(description="Test VAD pipeline")
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--send-only",
        action="store_true",
        help="Only send test audio, don't monitor results"
    )
    parser.add_argument(
        "--monitor-only",
        action="store_true",
        help="Only monitor results, don't send test audio"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Monitoring timeout in seconds"
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