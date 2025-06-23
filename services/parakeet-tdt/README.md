# Parakeet-TDT Speech-to-Text Service

NVIDIA Parakeet-TDT (Transducer-based Decoder with Time-synchronous decoding) service for converting VAD-filtered audio to word-by-word transcripts with timestamps.

## Overview

This service:
- Consumes VAD-filtered audio chunks from Kafka topic `media.audio.vad_filtered`
- Uses NVIDIA Parakeet-TDT-1.1B model for accurate speech recognition
- Produces word-level transcripts with timestamps to `media.text.transcribed.words`
- Supports both CPU and GPU inference (GPU recommended for performance)

## Features

- **Real-time Processing**: Processes audio chunks as they arrive from Kafka
- **Word-level Timestamps**: Provides precise timing for each transcribed word
- **High Accuracy**: Uses NVIDIA's state-of-the-art ASR model
- **Scalable**: Containerized with support for horizontal scaling
- **Monitoring**: Prometheus metrics and health check endpoints

## Configuration

Environment variables (with LOOM_ prefix):

```bash
LOOM_KAFKA_BOOTSTRAP_SERVERS=kafka:29092
LOOM_KAFKA_INPUT_TOPIC=media.audio.vad_filtered
LOOM_KAFKA_OUTPUT_TOPIC=media.text.transcribed.words
LOOM_MODEL_DEVICE=cpu  # or 'cuda' for GPU
LOOM_MODEL_CACHE_DIR=/models
LOOM_LOG_LEVEL=INFO
LOOM_HOST=0.0.0.0
LOOM_PORT=8002
```

## Input Schema

Expects VAD-filtered audio chunks with this structure:

```json
{
  "device_id": "string",
  "recorded_at": "2024-01-01T00:00:00Z",
  "audio_data": "base64-encoded-audio",
  "sample_rate": 16000,
  "format": "wav",
  "duration_seconds": 1.5,
  "chunk_id": "unique-chunk-id",
  "sequence_number": 1
}
```

## Output Schema

Produces word-by-word transcripts:

```json
{
  "device_id": "string",
  "recorded_at": "2024-01-01T00:00:00Z",
  "chunk_id": "unique-chunk-id",
  "words": [
    {
      "word": "hello",
      "start_time": 0.0,
      "end_time": 0.5,
      "confidence": 0.95
    },
    {
      "word": "world",
      "start_time": 0.6,
      "end_time": 1.0,
      "confidence": 0.92
    }
  ],
  "full_text": "hello world",
  "language": "en",
  "processing_time_ms": 150.5,
  "model_version": "nvidia/parakeet-tdt_ctc-1.1b"
}
```

## Development

```bash
# Install dependencies
make install

# Run development server
make dev

# Run tests
make test

# Build Docker image
make docker

# Run with GPU support
make docker-run-gpu
```

## API Endpoints

- `GET /` - Service info
- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe (checks model loading)
- `GET /metrics` - Prometheus metrics

## Performance

- **CPU**: ~500ms per second of audio (Intel i7)
- **GPU**: ~50ms per second of audio (NVIDIA T4)
- **Memory**: ~2GB for model + overhead
- **Startup**: 30-60s for initial model download

## Monitoring

Prometheus metrics available:
- `parakeet_audio_chunks_processed_total` - Total chunks processed
- `parakeet_transcripts_produced_total` - Total transcripts generated
- `parakeet_processing_duration_seconds` - Processing time histogram