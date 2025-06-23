#!/usr/bin/env python3
"""Test script for MiniCPM-Vision service."""

import base64
import json
import time
from datetime import datetime
from pathlib import Path

import httpx
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable


def create_test_image() -> str:
    """Create a simple test image and return as base64."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not installed. Using a simple 1x1 pixel image.")
        # Simple 1x1 white pixel PNG
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    # Create a test image with text
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some text
    draw.text((50, 50), "Test Image", fill='black')
    draw.text((50, 100), "MiniCPM Vision Test", fill='blue')
    draw.rectangle([20, 20, 380, 180], outline='red', width=2)
    
    # Convert to base64
    import io
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return img_str


def test_health_endpoints(base_url: str = "http://localhost:8003"):
    """Test health check endpoints."""
    print("Testing health endpoints...")
    
    try:
        # Test healthz
        response = httpx.get(f"{base_url}/healthz")
        print(f"  /healthz: {response.status_code} - {response.json()}")
        
        # Test readyz
        response = httpx.get(f"{base_url}/readyz")
        print(f"  /readyz: {response.status_code} - {response.json()}")
        
        # Test root
        response = httpx.get(f"{base_url}/")
        print(f"  /: {response.status_code} - {response.json()}")
        
        # Test status
        response = httpx.get(f"{base_url}/status")
        print(f"  /status: {response.status_code}")
        
    except Exception as e:
        print(f"  Error testing health endpoints: {e}")


def test_kafka_processing(
    bootstrap_servers: str = "localhost:9092",
    input_topic: str = "device.image.camera.raw",
    output_topic: str = "media.image.analysis.minicpm_results"
):
    """Test Kafka message processing."""
    print(f"\nTesting Kafka processing...")
    print(f"  Bootstrap servers: {bootstrap_servers}")
    print(f"  Input topic: {input_topic}")
    print(f"  Output topic: {output_topic}")
    
    try:
        # Create producer
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Create consumer
        consumer = KafkaConsumer(
            output_topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=30000  # 30 second timeout
        )
        
        # Create test message
        test_message = {
            "device_id": "test-device-001",
            "recorded_at": datetime.utcnow().isoformat(),
            "schema_version": "v1",
            "data": create_test_image(),
            "format": "png",
            "metadata": {
                "test": True,
                "source": "test-vision.py"
            }
        }
        
        print(f"  Sending test image to {input_topic}...")
        future = producer.send(input_topic, value=test_message)
        result = future.get(timeout=10)
        print(f"  Message sent: partition={result.partition}, offset={result.offset}")
        
        # Wait for processed message
        print(f"  Waiting for result on {output_topic}...")
        start_time = time.time()
        
        for message in consumer:
            if message.value.get('device_id') == test_message['device_id']:
                elapsed = time.time() - start_time
                print(f"  Result received after {elapsed:.2f}s")
                print(f"  Scene description: {message.value.get('scene_description')}")
                print(f"  Objects detected: {len(message.value.get('detected_objects', []))}")
                print(f"  OCR text: {message.value.get('full_text', 'None')}")
                print(f"  Processing time: {message.value.get('processing_time_ms')}ms")
                break
        else:
            print("  Timeout: No result received within 30 seconds")
        
        producer.close()
        consumer.close()
        
    except NoBrokersAvailable:
        print("  Error: Kafka broker not available")
    except Exception as e:
        print(f"  Error testing Kafka processing: {e}")


def main():
    """Run all tests."""
    print("MiniCPM-Vision Service Test\n")
    
    # Test HTTP endpoints
    test_health_endpoints()
    
    # Wait a bit for service to be ready
    print("\nWaiting 5 seconds for service to be fully ready...")
    time.sleep(5)
    
    # Test Kafka processing
    test_kafka_processing()
    
    print("\nTest completed!")


if __name__ == "__main__":
    main()