# MiniCPM-Vision Service

Vision-Language analysis service for Loom v2 using MiniCPM-Llama3-V 2.5 model.

## Overview

This service processes images from Kafka topics and performs comprehensive vision-language analysis including:
- Scene understanding and description
- Object detection
- OCR (Optical Character Recognition)
- Visual question answering
- Structured output generation using dottxt-ai/outlines

## Features

- **Multi-modal Analysis**: Processes images for scene understanding, object detection, and text extraction
- **Structured Output**: Uses outlines library for guaranteed JSON schema compliance
- **GPU/CPU Support**: Optimized for GPU but viable on CPU
- **Real-time Processing**: Consumes from Kafka topics in real-time
- **Health Monitoring**: Prometheus metrics and health check endpoints

## Architecture

```
Kafka Topics (Input)          MiniCPM-Vision Service          Kafka Topic (Output)
┌─────────────────────┐      ┌─────────────────────┐      ┌──────────────────────┐
│device.image.camera. │      │                     │      │media.image.analysis. │
│raw                  │─────▶│  Vision Processor   │─────▶│minicpm_results       │
├─────────────────────┤      │  - Scene Analysis   │      └──────────────────────┘
│device.video.screen. │      │  - Object Detection │
│raw                  │      │  - OCR              │
└─────────────────────┘      │  - Structured Output│
                             └─────────────────────┘
```

## Configuration

Environment variables (with `LOOM_` prefix):

| Variable | Description | Default |
|----------|-------------|---------|
| `LOOM_KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `kafka:29092` |
| `LOOM_KAFKA_INPUT_TOPICS` | Input topics | `["device.image.camera.raw", "device.video.screen.raw"]` |
| `LOOM_KAFKA_OUTPUT_TOPIC` | Output topic | `media.image.analysis.minicpm_results` |
| `LOOM_MODEL_DEVICE` | Device for inference | `None` (auto-detect) |
| `LOOM_LOG_LEVEL` | Log level | `INFO` |

## Development

```bash
# Install dependencies
make install

# Run development server
make dev

# Run tests
make test

# Run full CI pipeline
make ci

# Build Docker image
make docker
```

## API Endpoints

- `GET /` - Service information
- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe
- `GET /metrics` - Prometheus metrics
- `GET /status` - Detailed service status

## Output Schema

The service produces structured JSON output with the following fields:

```json
{
  "device_id": "string",
  "recorded_at": "datetime",
  "scene_description": "string",
  "scene_categories": ["string"],
  "detected_objects": [
    {
      "label": "string",
      "confidence": 0.95,
      "bbox": [x1, y1, x2, y2]
    }
  ],
  "ocr_results": [
    {
      "text": "string",
      "confidence": 0.89,
      "bbox": [x1, y1, x2, y2]
    }
  ],
  "full_text": "string",
  "processing_time_ms": 1234.5,
  "model_version": "MiniCPM-Llama3-V-2.5"
}
```

## Model Information

- **Model**: [MiniCPM-Llama3-V 2.5](https://huggingface.co/openbmb/MiniCPM-Llama3-V-2_5)
- **Size**: ~8GB
- **Capabilities**: Vision-language understanding, OCR, object detection
- **Performance**: GPU recommended for real-time processing

## Resource Requirements

- **Memory**: 4-8GB minimum (8GB recommended)
- **GPU**: Optional but recommended for performance
- **Storage**: ~10GB for model weights