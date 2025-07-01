#!/usr/bin/env python3
"""Test the AudioChunk model field mapping"""

import json
from app.models import AudioChunk

# Test data that mimics what's coming from ingestion API
test_message = {
    "schema_version": "1.0",
    "device_id": "test-device",
    "recorded_at": "2025-07-01T19:30:00Z",
    "timestamp": "2025-07-01T19:30:00Z",
    "message_id": "test-msg-123",
    "data": "base64encodedaudiodata",  # This is what ingestion API sends
    "sample_rate": 16000,
    "channels": 1,
    "format": "wav",
    "duration_ms": 5000,
    "file_id": "chunk_0"
}

print("Testing AudioChunk model with ingestion API data...")
print(f"Input data: {json.dumps(test_message, indent=2)}")

try:
    chunk = AudioChunk(**test_message)
    print("\n✅ SUCCESS: AudioChunk created successfully!")
    print(f"  - device_id: {chunk.device_id}")
    print(f"  - chunk_id: {chunk.get_chunk_id()}")
    print(f"  - audio_data: {chunk.get_audio_data()[:20]}...")
    print(f"  - duration_ms: {chunk.get_duration_ms()}")
    print(f"  - duration_seconds: {chunk.get_duration_seconds()}")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")

# Test with old field names (should also work)
print("\n\nTesting with legacy field names...")
legacy_message = {
    "schema_version": "1.0",
    "device_id": "test-device",
    "recorded_at": "2025-07-01T19:30:00Z",
    "audio_data": "base64encodedaudiodata",  # Old field name
    "sample_rate": 16000,
    "format": "wav",
    "duration_seconds": 5.0,  # Old field name
    "chunk_id": "chunk-123",  # Old field name
    "sequence_number": 42  # Old field name
}

try:
    chunk = AudioChunk(**legacy_message)
    print("\n✅ SUCCESS: AudioChunk created with legacy fields!")
    print(f"  - device_id: {chunk.device_id}")
    print(f"  - chunk_id: {chunk.get_chunk_id()}")
    print(f"  - audio_data: {chunk.get_audio_data()[:20]}...")
    print(f"  - duration_ms: {chunk.get_duration_ms()}")
    print(f"  - duration_seconds: {chunk.get_duration_seconds()}")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")