# Nomic Embed Vision Service

A high-performance text and image embedding service using Nomic Embed Vision v1.5 for the Loom v2 data pipeline.

## Overview

This service provides unified text and image embeddings using the state-of-the-art [Nomic Embed Vision v1.5](https://huggingface.co/nomic-ai/nomic-embed-vision-v1.5) model. It processes data from Kafka topics and generates embeddings that are sent to output topics for storage and retrieval.

## Features

- **Unified Text & Image Embeddings**: Single model for both text and image data
- **High Performance**: Batch processing with configurable concurrency
- **GPU Support**: Automatic GPU detection and fallback to CPU
- **Kafka Integration**: Consumes from multiple input topics and produces to embedding topics
- **REST API**: Direct embedding generation via HTTP endpoints
- **Health Monitoring**: Comprehensive health checks and processing statistics
- **Scalable**: Configurable worker concurrency and batch sizes

## Model Information

- **Model**: [nomic-ai/nomic-embed-vision-v1.5](https://huggingface.co/nomic-ai/nomic-embed-vision-v1.5)
- **Embedding Dimension**: 768
- **Supported Inputs**: Text (up to 8K characters), Images (JPEG, PNG, etc.)
- **Performance**: Optimized for batch processing with GPU acceleration

## API Endpoints

### Health & Status

```bash
# Health check
GET /healthz

# Processing statistics
GET /stats

# Model information
GET /model/info
```

### Embedding Generation

```bash
# Single embedding (text and/or image)
POST /embed
{
  "text": "Your text here",
  "image_data": "base64-encoded-image",
  "include_description": true
}

# Batch embeddings
POST /embed/batch
{
  "texts": ["text1", "text2"],
  "images": ["base64-image1", "base64-image2"],
  "include_descriptions": true
}
```

### Model Management

```bash
# Reload model
POST /model/reload
```

## Kafka Integration

### Input Topics (Consumes From)

**Text Topics:**
- `device.text.notes.raw` - User notes and memos
- `media.text.transcribed.words` - Transcribed speech
- `task.url.processed.content` - Processed web content
- `task.github.processed.content` - GitHub repository content
- `task.document.processed.content` - Document processing results

**Image Topics:**
- `device.image.camera.raw` - Camera captures and screenshots
- `device.video.screen.raw` - Screen recording frames

### Output Topics (Produces To)

- `embeddings.text.nomic` - Text embeddings with metadata
- `embeddings.image.nomic` - Image embeddings with metadata

## Configuration

### Environment Variables

```bash
# Service Configuration
NOMIC_EMBED_HOST=0.0.0.0
NOMIC_EMBED_PORT=8004
NOMIC_EMBED_LOG_LEVEL=INFO

# Model Configuration
NOMIC_EMBED_MODEL_NAME=nomic-ai/nomic-embed-vision-v1.5
NOMIC_EMBED_DEVICE=auto  # auto, cpu, cuda
NOMIC_EMBED_MAX_BATCH_SIZE=32
NOMIC_EMBED_MODEL_CACHE_DIR=./models

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
NOMIC_EMBED_KAFKA_GROUP_ID=nomic-embed-group

# Processing Configuration
NOMIC_EMBED_MAX_TEXT_LENGTH=8192
NOMIC_EMBED_MAX_IMAGE_SIZE=2048
NOMIC_EMBED_WORKER_CONCURRENCY=4
NOMIC_EMBED_MAX_QUEUE_SIZE=1000
```

## Development

### Setup

```bash
# Install dependencies
make install

# Run development server
make dev

# Run tests
make test

# Format and lint code
make format
make lint
make type-check
```

### Docker

```bash
# Build image
make docker

# Run container
docker run -p 8004:8004 \
  -e KAFKA_BOOTSTRAP_SERVERS=host.docker.internal:9092 \
  loom/nomic-embed:latest
```

## Usage Examples

### Direct API Usage

```python
import requests
import base64

# Text embedding
response = requests.post("http://localhost:8004/embed", json={
    "text": "This is a sample text for embedding"
})
text_embedding = response.json()["text_embedding"]

# Image embedding
with open("image.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = requests.post("http://localhost:8004/embed", json={
    "image_data": image_data,
    "include_description": True
})
image_embedding = response.json()["image_embedding"]
description = response.json()["image_description"]
```

### Batch Processing

```python
# Batch embeddings
response = requests.post("http://localhost:8004/embed/batch", json={
    "texts": ["Text 1", "Text 2", "Text 3"],
    "images": [image_data1, image_data2],
    "include_descriptions": True
})

batch_result = response.json()
text_embeddings = batch_result["text_embeddings"]
image_embeddings = batch_result["image_embeddings"]
```

## Performance

### Benchmarks

- **Text Processing**: ~100 texts/second (CPU), ~500 texts/second (GPU)
- **Image Processing**: ~20 images/second (CPU), ~100 images/second (GPU)
- **Memory Usage**: ~2GB (CPU), ~4GB (GPU with model)
- **Batch Efficiency**: 3-5x faster than individual requests

### Optimization Tips

1. **Use Batch Endpoints**: Much more efficient than individual requests
2. **GPU Acceleration**: Significant performance improvement with CUDA
3. **Adjust Batch Size**: Increase for more memory, decrease for lower latency
4. **Concurrency**: Scale workers based on available CPU/GPU resources

## Monitoring

### Health Checks

```bash
curl http://localhost:8004/healthz
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "nomic-ai/nomic-embed-vision-v1.5",
  "device": "cuda",
  "total_processed": 1234,
  "queue_size": 5
}
```

### Processing Statistics

```bash
curl http://localhost:8004/stats
```

Response:
```json
{
  "total_text_processed": 1000,
  "total_images_processed": 250,
  "average_text_processing_time_ms": 15.5,
  "average_image_processing_time_ms": 45.2,
  "queue_size": 5,
  "model_memory_usage_mb": 3456.7,
  "uptime_seconds": 3600
}
```

## Integration with Loom v2

This service automatically integrates with the Loom v2 pipeline:

1. **Data Flow**: Consumes processed data from various topics
2. **Embedding Storage**: Produces embeddings to dedicated topics
3. **Database Integration**: Embeddings are stored in TimescaleDB via kafka-to-db consumer
4. **Search & Retrieval**: Embeddings enable semantic search across all user data

## Troubleshooting

### Common Issues

**Model Download Failed**
```bash
# Check internet connection and HuggingFace access
# Increase timeout or download model manually
```

**GPU Not Detected**
```bash
# Check CUDA installation
nvidia-smi

# Verify PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"
```

**High Memory Usage**
```bash
# Reduce batch size
export NOMIC_EMBED_MAX_BATCH_SIZE=16

# Use CPU instead of GPU
export NOMIC_EMBED_DEVICE=cpu
```

### Logs

```bash
# View container logs
docker logs -f loom-nomic-embed

# View specific log levels
docker logs loom-nomic-embed 2>&1 | grep ERROR
```

## Contributing

1. Follow the existing code style (black + ruff)
2. Add tests for new functionality
3. Update documentation
4. Ensure type hints are complete

## License

Part of the Loom v2 project - internal use only.