# Kafka Test Producer

A REST API service for generating and sending example messages to any Kafka topic in the Loom v2 system. This service is useful for testing consumers, debugging pipelines, and demonstrating the system.

## Features

- Generate realistic example payloads for all Kafka topics
- Send single or bulk messages via REST API
- Custom payload support
- Automatic example generation for known topics
- Health check endpoint
- Structured logging

## API Endpoints

### Root
- `GET /` - Service information and available endpoints

### Health
- `GET /health` - Health check with Kafka connectivity status

### Topics
- `GET /topics` - List all available topics grouped by category
- `GET /topics/{topic}` - Get example payload for a specific topic
- `GET /examples` - Get example payloads for all topics

### Message Sending
- `POST /send` - Send message(s) to a single topic
- `POST /send/bulk` - Send messages to multiple topics

## Usage Examples

### List Available Topics
```bash
curl http://localhost:8008/topics | jq
```

### Get Example Payload for a Topic
```bash
curl http://localhost:8008/topics/device.audio.raw | jq
```

### Send Example Message to a Topic
```bash
# Send single message with auto-generated example
curl -X POST http://localhost:8008/send \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "device.audio.raw",
    "count": 1
  }' | jq

# Send multiple messages
curl -X POST http://localhost:8008/send \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "device.sensor.gps.raw",
    "count": 5
  }' | jq
```

### Send Custom Message
```bash
curl -X POST http://localhost:8008/send \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "task.url.ingest",
    "message": {
      "schema_version": "v1",
      "trace_id": "custom-trace-123",
      "timestamp": "2025-06-26T10:00:00Z",
      "data": {
        "url": "https://example.com/test",
        "url_type": "webpage",
        "priority": "high"
      }
    }
  }' | jq
```

### Send to Multiple Topics
```bash
curl -X POST http://localhost:8008/send/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "topics": ["device.audio.raw", "device.sensor.gps.raw", "external.twitter.liked.raw"],
    "count_per_topic": 3
  }' | jq
```

## Supported Topics

### Device Data
- `device.audio.raw` - Raw audio chunks
- `device.video.screen.raw` - Screen recording keyframes
- `device.image.camera.raw` - Camera photos and screenshots
- `device.sensor.gps.raw` - GPS location data
- `device.sensor.accelerometer.raw` - Motion sensor data
- `device.health.heartrate.raw` - Heart rate measurements
- `device.state.power.raw` - Battery and power status

### External Sources
- `external.twitter.liked.raw` - Liked tweets
- `external.twitter.images.raw` - Twitter screenshots for OCR

### Media Processing
- `media.audio.vad_filtered` - Speech-detected audio
- `media.text.transcribed.words` - Speech transcriptions

### Analysis
- `analysis.text.embedded.twitter` - Twitter content with embeddings

### Tasks
- `task.url.ingest` - URLs to be processed

## Example Payloads

Each topic has realistic example data that matches the actual schema used in production:

### Device Audio Example
```json
{
  "schema_version": "v1",
  "device_id": "laptop-1",
  "timestamp": "2025-06-26T10:00:00.000Z",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "audio_data": "RkFLRV9BVURJT19EQVRB...",
    "format": "pcm",
    "sample_rate": 16000,
    "channels": 1,
    "duration_ms": 1000
  }
}
```

### Twitter Image Example
```json
{
  "schema_version": "v1",
  "trace_id": "550e8400-e29b-41d4-a716-446655440001",
  "tweet_id": "1234567890123456789",
  "tweet_url": "https://x.com/user/status/1234567890123456789",
  "data": {
    "image_data": "RkFLRV9UV0lUVEVSX1NDUkVFTlNIT1Q=...",
    "format": "png",
    "width": 1200,
    "height": 800
  }
}
```

## Development

### Running Locally
```bash
cd services/kafka-test-producer
pip install -r requirements.txt
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 uvicorn app.main:app --reload
```

### Docker
```bash
docker compose up kafka-test-producer
```

## Environment Variables

- `KAFKA_BOOTSTRAP_SERVERS` - Kafka broker addresses (default: `kafka:29092`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Testing the Pipeline

Use this service to test the entire data pipeline:

1. **Test Audio Processing Pipeline**:
   ```bash
   # Send audio → VAD → Transcription → Embeddings
   curl -X POST http://localhost:8008/send -d '{"topic": "device.audio.raw", "count": 5}'
   ```

2. **Test Twitter OCR Pipeline**:
   ```bash
   # Send Twitter image → Moondream OCR → Database
   curl -X POST http://localhost:8008/send -d '{"topic": "external.twitter.images.raw"}'
   ```

3. **Test Sensor Data Pipeline**:
   ```bash
   # Send GPS data → Database with retention
   curl -X POST http://localhost:8008/send -d '{"topic": "device.sensor.gps.raw", "count": 10}'
   ```

## Monitoring

The service provides structured JSON logs that can be monitored:

```bash
docker logs loomv2-kafka-test-producer-1 -f | jq
```