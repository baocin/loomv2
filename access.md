# Loom v2 Service Access Guide

Complete guide for accessing every service in the Loom v2 stack including connection strings, passwords, Kafka topics, API endpoints, and data formats.

## 🗄️ Database Access

### PostgreSQL/TimescaleDB Connection

**Connection String:**
```bash
postgresql://loom:loom@localhost:5432/loom
```

**Individual Connection Parameters:**
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `loom`
- **Username:** `loom`
- **Password:** `loom`

**Direct Connection Methods:**

```bash
# psql command line (if psql installed on host) - ✅ WORKING
psql postgresql://loom:loom@localhost:5432/loom

# Docker exec into container (recommended)
docker exec -it loomv2-postgres-1 psql -U loom -d loom

# For scripts/non-interactive use
docker exec loomv2-postgres-1 psql -U loom -d loom -c "SELECT version();"

# Connection via GUI tools (DBeaver, pgAdmin, etc.) - ✅ WORKING
Host: localhost
Port: 5432
Database: loom
Username: loom
Password: loom
SSL Mode: Disable (for local development)
```

**Common Database Queries:**

```sql
-- View all tables
\dt

-- View table schemas
\d+ device_audio_raw

-- Sample queries
SELECT COUNT(*) FROM device_audio_raw;
SELECT device_id, recorded_at FROM device_sensor_gps_raw LIMIT 10;
SELECT * FROM media_audio_vad_filtered ORDER BY timestamp DESC LIMIT 5;

-- View active connections
SELECT * FROM pg_stat_activity WHERE datname = 'loom';

-- Database size information
SELECT pg_size_pretty(pg_database_size('loom')) as database_size;
```

## 📊 Kafka Access

### Kafka Connection Details

**Bootstrap Servers:** `localhost:9092`
**Admin Port:** `9093`

### Kafka Web UI Access

**Kafka UI Dashboard:** http://localhost:8081

Features:
- View topics and partitions
- Browse messages in real-time
- Monitor consumer groups
- View topic configurations
- Message search and filtering

### Command Line Kafka Access

**View Available Topics:**
```bash
# List all topics via Docker
docker exec loomv2-kafka-1 kafka-topics --bootstrap-server localhost:9092 --list

# Or via external Kafka client (if installed)
kafka-topics --bootstrap-server localhost:9092 --list
```

**View Topic Contents:**

```bash
# Raw device audio data
docker exec -it loomv2-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic device.audio.raw \
  --from-beginning

# GPS sensor data with key information
docker exec -it loomv2-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic device.sensor.gps.raw \
  --property print.key=true \
  --property key.separator=" | " \
  --from-beginning

# Processed AI data
docker exec -it loomv2-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic media.audio.vad_filtered \
  --from-beginning

# System app monitoring
docker exec -it loomv2-kafka-1 kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic device.system.apps.macos.raw \
  --from-beginning
```

**Topic Information:**
```bash
# Get topic details
docker exec -it loomv2-kafka-1 kafka-topics \
  --bootstrap-server localhost:9092 \
  --describe \
  --topic device.audio.raw

# View consumer groups
docker exec -it loomv2-kafka-1 kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list

# Consumer group lag
docker exec -it loomv2-kafka-1 kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group <group-name>
```

## 🌐 API Endpoints

### Ingestion API Base URL

**Local Development:** http://localhost:8000
**Swagger Documentation:** http://localhost:8000/docs
**ReDoc Documentation:** http://localhost:8000/redoc

### Health and Monitoring Endpoints

```bash
# Liveness probe (always returns 200) - NO API KEY REQUIRED
curl http://localhost:8000/healthz

# Readiness probe (returns 200 when dependencies healthy) - NO API KEY REQUIRED
curl http://localhost:8000/readyz

# Prometheus metrics - NO API KEY REQUIRED
curl http://localhost:8000/metrics
```

### API Authentication

**All data endpoints require an API key:**
- **Header Name:** `X-API-Key`
- **API Key:** `pineapple`

Example:
```bash
curl -H "X-API-Key: apikeyhere" http://localhost:8000/audio/upload
```

### Audio Endpoints

**Upload Audio Chunk:**
```bash
curl -X POST http://localhost:8000/audio/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "chunk_data": "dGVzdCBhdWRpbyBkYXRh",
    "sample_rate": 16000,
    "channels": 1,
    "duration_ms": 3000,
    "format": "wav"
  }'
```

**WebSocket Audio Streaming:**
```javascript
// Connect to WebSocket (Note: WebSocket auth requires API key in first message)
const ws = new WebSocket('ws://localhost:8000/audio/stream/12345678-1234-1234-1234-123456789012');

// Send audio chunk
ws.send(JSON.stringify({
  "message_type": "audio_chunk",
  "data": {
    "recorded_at": "2024-01-23T10:30:00Z",
    "chunk_data": "dGVzdCBhdWRpbyBkYXRh",
    "chunk_index": 0,
    "sample_rate": 16000,
    "channels": 1,
    "bits_per_sample": 16,
    "duration_ms": 1000,
    "format": "pcm"
  }
}));

// Send ping
ws.send(JSON.stringify({
  "message_type": "ping",
  "data": {"timestamp": "2024-01-23T10:30:00Z"}
}));
```

### Sensor Endpoints

**GPS Data:**
```bash
curl -X POST http://localhost:8000/sensor/gps \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 52.0,
    "accuracy": 5.0,
    "speed": 0.0,
    "heading": 0.0
  }'
```

**Accelerometer Data:**
```bash
curl -X POST http://localhost:8000/sensor/accelerometer \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "x": 0.1,
    "y": 0.2,
    "z": 9.8
  }'
```

**Heart Rate Data:**
```bash
curl -X POST http://localhost:8000/sensor/heartrate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "bpm": 72,
    "confidence": 0.95
  }'
```

**Power State:**
```bash
curl -X POST http://localhost:8000/sensor/power \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "battery_level": 85,
    "is_charging": false,
    "power_source": "battery"
  }'
```

### Image/Media Endpoints

**Upload Image:**
```bash
curl -X POST http://localhost:8000/images/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==",
    "width": 1920,
    "height": 1080,
    "format": "jpeg",
    "camera_type": "front",
    "file_size": 2048,
    "metadata": {"test": true}
  }'
```

### System Monitoring Endpoints

**macOS App Monitoring:**
```bash
curl -X POST http://localhost:8000/system/apps/macos \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "running_applications": [
      {
        "pid": 1234,
        "name": "Visual Studio Code",
        "bundle_id": "com.microsoft.VSCode",
        "active": true,
        "hidden": false
      },
      {
        "pid": 5678,
        "name": "Safari",
        "bundle_id": "com.apple.Safari",
        "active": false,
        "hidden": false
      }
    ]
  }'
```

**Device Metadata:**
```bash
curl -X POST http://localhost:8000/system/metadata \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "metadata_type": "device_capabilities",
    "metadata": {
      "sensors": ["accelerometer", "gyroscope", "gps"],
      "cameras": {"front": true, "rear": true, "resolution": "1920x1080"},
      "audio": {
        "microphone": true,
        "speakers": true,
        "sample_rates": [44100, 48000]
      },
      "connectivity": ["wifi", "bluetooth", "cellular"]
    }
  }'
```

### Notes/Content Endpoints

**Upload Note:**
```bash
curl -X POST http://localhost:8000/notes/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "title": "My Note",
    "content": "# Header\n\nThis is **bold** text with a [link](https://example.com).",
    "note_type": "markdown",
    "tags": ["work", "important"]
  }'
```

### GitHub Processing Endpoints

**Submit GitHub Repository for Processing:**
```bash
curl -X POST http://localhost:8000/github/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "url": "https://github.com/octocat/Hello-World",
    "repository_type": "repository",
    "priority": 5,
    "include_files": ["*.py", "*.md", "*.txt"],
    "exclude_files": ["*.pyc", "__pycache__/*"],
    "max_file_size": 1048576,
    "extract_options": {"extract_readme": true, "extract_code": true}
  }'
```

### Document Processing Endpoints

**Upload Document for Processing:**
```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: apikeyhere" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "filename": "document.pdf",
    "file_data": "JVBERi0xLjQKJcOkw7zDssO4CjIgMCBvYmo8PC9MZW5ndGggMyAwIFI+PnN0cmVhbQp4nHPOOOKM",
    "content_type": "application/pdf",
    "file_size": 102400,
    "document_type": "pdf",
    "priority": 5,
    "extract_options": {"extract_text": true},
    "metadata": {"source": "user_upload"}
  }'
```

## 🤖 AI Service APIs

### OneFileLLM Service (Port 8080)

**Base URL:** http://localhost:8080

**Health Check:**
```bash
# Health status - NO API KEY REQUIRED
curl http://localhost:8080/health
```

**Process Text Content:**
```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This is a test document for processing.",
    "content_type": "text/plain",
    "options": {
      "extract_metadata": true,
      "analyze_content": true,
      "max_tokens": 1000
    }
  }'
```

**Process GitHub Repository:**
```bash
curl -X POST http://localhost:8080/process-github \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/raphaelsty/onefilellm",
    "include_files": ["*.py", "*.md"],
    "exclude_files": ["*.pyc", "__pycache__/*"],
    "max_file_size": 1048576,
    "options": {
      "extract_readme": true,
      "extract_code": true,
      "include_comments": true
    }
  }'
```

**Process Document File:**
```bash
curl -X POST http://localhost:8080/process-document \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "document.pdf",
    "file_data": "base64-encoded-content",
    "content_type": "application/pdf",
    "options": {
      "extract_text": true,
      "extract_metadata": true,
      "analyze_structure": true
    }
  }'
```

### Silero VAD Service (Port 8001)

**Base URL:** http://localhost:8001

**Health Check:**
```bash
# Health status - NO API KEY REQUIRED
curl http://localhost:8001/healthz
```

**Voice Activity Detection:**
```bash
curl -X POST http://localhost:8001/detect \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64-encoded-audio-data",
    "sample_rate": 16000,
    "threshold": 0.5,
    "min_speech_duration": 0.25,
    "min_silence_duration": 0.1
  }'
```

**Response Format:**
```json
{
  "speech_segments": [
    {
      "start": 0.5,
      "end": 3.2,
      "confidence": 0.95
    }
  ],
  "has_speech": true,
  "total_speech_duration": 2.7,
  "total_duration": 5.0
}
```

**Batch VAD Processing:**
```bash
curl -X POST http://localhost:8001/detect-batch \
  -H "Content-Type: application/json" \
  -d '{
    "audio_chunks": [
      {
        "audio_data": "base64-chunk-1",
        "sample_rate": 16000,
        "chunk_id": "chunk_001"
      },
      {
        "audio_data": "base64-chunk-2",
        "sample_rate": 16000,
        "chunk_id": "chunk_002"
      }
    ],
    "threshold": 0.5
  }'
```

### Parakeet TDT ASR Service (Port 8002)

**Base URL:** http://localhost:8002

**Health Check:**
```bash
# Health status - NO API KEY REQUIRED
curl http://localhost:8002/healthz
```

**Speech-to-Text Transcription:**
```bash
curl -X POST http://localhost:8002/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64-encoded-audio-data",
    "sample_rate": 16000,
    "language": "en",
    "return_word_timestamps": true,
    "return_confidence": true
  }'
```

**Response Format:**
```json
{
  "text": "Hello, this is a test transcription.",
  "language": "en",
  "confidence": 0.98,
  "words": [
    {
      "word": "Hello",
      "start": 0.0,
      "end": 0.5,
      "confidence": 0.99
    },
    {
      "word": "this",
      "start": 0.6,
      "end": 0.8,
      "confidence": 0.97
    }
  ],
  "duration": 3.5
}
```

**Streaming Transcription:**
```bash
curl -X POST http://localhost:8002/transcribe-stream \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64-encoded-audio-chunk",
    "sample_rate": 16000,
    "stream_id": "stream_123",
    "is_final": false
  }'
```

### MiniCPM Vision Service (Port 8003)

**Base URL:** http://localhost:8003

**Health Check:**
```bash
# Health status - NO API KEY REQUIRED
curl http://localhost:8003/healthz
```

**Image Analysis:**
```bash
curl -X POST http://localhost:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "base64-encoded-image-data",
    "prompt": "Describe what you see in this image in detail.",
    "max_tokens": 200,
    "temperature": 0.7
  }'
```

**Response Format:**
```json
{
  "description": "This image shows a modern office workspace with a laptop computer, coffee cup, and notebook on a wooden desk.",
  "objects_detected": [
    {"object": "laptop", "confidence": 0.95, "bbox": [100, 150, 300, 250]},
    {"object": "coffee_cup", "confidence": 0.89, "bbox": [350, 200, 380, 280]},
    {"object": "notebook", "confidence": 0.92, "bbox": [50, 180, 180, 300]}
  ],
  "scene_type": "indoor_office",
  "confidence": 0.94
}
```

**OCR Text Extraction:**
```bash
curl -X POST http://localhost:8003/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "base64-encoded-image-data",
    "extract_text_only": true,
    "language": "en"
  }'
```

**Response Format:**
```json
{
  "text": "Extracted text content from the image",
  "text_regions": [
    {
      "text": "Header Text",
      "bbox": [10, 20, 200, 50],
      "confidence": 0.96
    },
    {
      "text": "Body paragraph content",
      "bbox": [10, 60, 300, 120],
      "confidence": 0.93
    }
  ],
  "language": "en"
}
```

**Vision Question Answering:**
```bash
curl -X POST http://localhost:8003/vqa \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "base64-encoded-image-data",
    "question": "How many people are in this image?",
    "max_tokens": 50
  }'
```

### AI Service Status Dashboard

**Check All AI Services:**
```bash
# Health check all services at once
for port in 8080 8001 8002 8003 8004; do
  service_name=""
  case $port in
    8080) service_name="OneFileLLM" ;;
    8001) service_name="Silero VAD" ;;
    8002) service_name="Parakeet TDT" ;;
    8003) service_name="MiniCPM Vision" ;;
    8004) service_name="Nomic Embed" ;;
  esac

  echo -n "$service_name (port $port): "
  if curl -s -f "http://localhost:$port/health" > /dev/null 2>&1 || curl -s -f "http://localhost:$port/healthz" > /dev/null 2>&1; then
    echo "✅ RUNNING"
  else
    echo "❌ DOWN"
  fi
done
```

**AI Service Docker Container Management:**
```bash
# View AI service containers
docker ps | grep -E "(onefilellm|silero|parakeet|minicpm|nomic)"

# Restart specific AI service
docker restart loomv2-onefilellm-1
docker restart loomv2-silero-vad-1
docker restart loomv2-parakeet-tdt-1
docker restart loomv2-minicpm-vision-1
docker restart loomv2-nomic-embed-1

# View AI service logs
docker logs -f loomv2-onefilellm-1
docker logs -f loomv2-silero-vad-1
docker logs -f loomv2-parakeet-tdt-1
docker logs -f loomv2-minicpm-vision-1
docker logs -f loomv2-nomic-embed-1
```

### Nomic Embed Vision Service (Port 8004)

**Base URL:** http://localhost:8004

**Health Check:**
```bash
# Health status - NO API KEY REQUIRED
curl http://localhost:8004/healthz
```

**Text Embedding:**
```bash
curl -X POST http://localhost:8004/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a sample text for embedding generation",
    "metadata": {"source": "manual_test"}
  }'
```

**Image Embedding:**
```bash
curl -X POST http://localhost:8004/embed \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "base64-encoded-image-data",
    "include_description": true,
    "metadata": {"source": "manual_test"}
  }'
```

**Combined Text & Image Embedding:**
```bash
curl -X POST http://localhost:8004/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Describe this image",
    "image_data": "base64-encoded-image-data",
    "include_description": true
  }'
```

**Response Format:**
```json
{
  "text_embedding": [0.1, 0.2, 0.3, ...],
  "image_embedding": [0.4, 0.5, 0.6, ...],
  "image_description": "Description of the image",
  "embedding_model": "nomic-ai/nomic-embed-vision-v1.5",
  "embedding_dimension": 768,
  "processing_time_ms": 45.2,
  "message_id": "uuid-here"
}
```

**Batch Embeddings:**
```bash
curl -X POST http://localhost:8004/embed/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "First text to embed",
      "Second text to embed"
    ],
    "images": [
      "base64-image-1",
      "base64-image-2"
    ],
    "include_descriptions": true,
    "batch_id": "batch-123"
  }'
```

**Model Information:**
```bash
curl http://localhost:8004/model/info
```

**Processing Statistics:**
```bash
curl http://localhost:8004/stats
```

**Model Reload:**
```bash
curl -X POST http://localhost:8004/model/reload
```

## 📋 Data Source Expected Formats

### Device ID Format
All endpoints require a valid UUID format for device_id:
```
Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Example: 12345678-1234-1234-1234-123456789012
```

### Timestamp Format
All recorded_at fields must be ISO 8601 UTC timestamps:
```
Format: YYYY-MM-DDTHH:mm:ss.sssZ
Example: 2024-01-23T10:30:00.000Z
```

### Binary Data Encoding
Audio chunks and image data must be base64 encoded:
```python
import base64
audio_bytes = b"raw audio data"
encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')
```

### Message Structure
All Kafka messages follow this base structure:
```json
{
  "schema_version": "1.0",
  "device_id": "12345678-1234-1234-1234-123456789012",
  "recorded_at": "2024-01-23T10:30:00.000Z",
  "timestamp": "2024-01-23T10:30:01.000Z",
  "message_id": "uuid-generated-by-server",
  // ... endpoint-specific data
}
```

## 🎯 Topic-to-Endpoint Mapping

| API Endpoint | Kafka Topic | Data Type |
|--------------|-------------|-----------|
| `/audio/upload` | `device.audio.raw` | Raw audio chunks |
| `/images/upload` | `device.image.camera.raw` | Camera/screenshot images |
| `/sensor/gps` | `device.sensor.gps.raw` | GPS coordinates |
| `/sensor/accelerometer` | `device.sensor.accelerometer.raw` | Motion data |
| `/sensor/heartrate` | `device.health.heartrate.raw` | Heart rate measurements |
| `/sensor/power` | `device.state.power.raw` | Battery/power state |
| `/system/apps/macos` | `device.system.apps.macos.raw` | Running applications |
| `/system/metadata` | `device.metadata.raw` | Device capabilities |

## 🔬 AI Processing Pipeline Topics

| Topic | Data Type | Source |
|-------|-----------|--------|
| `media.audio.vad_filtered` | Voice activity detected audio | Silero VAD processing |
| `media.audio.voice_segments` | Speech segment boundaries | VAD post-processing |
| `media.text.word_timestamps` | Transcribed words with timing | NVIDIA Parakeet-TDT |
| `media.image.vision_annotations` | Object/scene analysis | MiniCPM-Llama3-V |
| `analysis.audio.emotion_scores` | Speech emotion recognition | Laion BUD-E-Whisper |
| `analysis.image.face_emotions` | Face emotion detection | Empathic-Insight-Face |
| `task.url.processed_content` | Web content extraction | URL processor |
| `processed.github.parsed` | Processed GitHub repositories | OneFileLLM GitHub processor |
| `processed.document.parsed` | Processed documents | OneFileLLM document processor |

## 🐳 Container Management

### View Running Services
```bash
# Docker containers
docker ps

# Container logs
docker logs -f loomv2-ingestion-api-1
docker logs -f loomv2-kafka-1
docker logs -f loomv2-postgres-1
docker logs -f loomv2-kafka-ui-1

# All services logs
docker-compose logs -f
```

### Restart Services
```bash
# Restart all services
docker-compose down && docker-compose up -d

# Restart specific service
docker-compose restart ingestion-api
docker-compose restart kafka
docker-compose restart postgres

# View service health
docker-compose ps
```

## 🧪 Testing & Validation

### End-to-End Testing
```bash
# Run complete e2e test suite
make test-e2e

# Run specific service tests
cd services/ingestion-api && make test

# Integration tests
make test-integration
```

### Manual Testing
```bash
# Test API health
curl http://localhost:8000/healthz

# Test database connection
make db-connect

# Test Kafka connectivity
make topics-list

# View Kafka UI
open http://localhost:8081
```

## 🔧 Environment Variables

### Core Configuration
```bash
# Database
LOOM_DATABASE_URL="postgresql://loom:loom@localhost:5432/loom"

# Kafka
LOOM_KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
LOOM_KAFKA_TOPIC_PREFIX="loom"

# API Server
LOOM_HOST="0.0.0.0"
LOOM_PORT=8000
LOOM_LOG_LEVEL="INFO"
LOOM_CORS_ORIGINS="*"

# Development
LOOM_ENVIRONMENT="development"
LOOM_DEBUG=true
```

### Override Configuration
```bash
# Set environment variables
export LOOM_LOG_LEVEL=DEBUG
export LOOM_DATABASE_URL="postgresql://custom:custom@remote:5432/loom"

# Or create .env file in project root
echo "LOOM_LOG_LEVEL=DEBUG" > .env
```

## 🚨 Troubleshooting

### Common Issues

**Service Not Responding:**
```bash
# Check if development environment is running
make status

# Start services if stopped
make dev-up

# Check specific service logs
kubectl logs deployment/ingestion-api -n loom-dev
```

**Database Connection Failed:**
```bash
# Verify PostgreSQL container is running
docker ps | grep postgres

# Check container health
docker exec loomv2-postgres-1 pg_isready -U loom -d loom

# Test container internal connection
docker exec -it loomv2-postgres-1 psql -U loom -d loom

# Check port binding
docker port loomv2-postgres-1

# Restart PostgreSQL if needed
docker compose -f docker-compose.local.yml restart postgres

# Check logs for errors
docker logs loomv2-postgres-1 --tail 50
```

**Kafka Topics Missing:**
```bash
# Create topics manually
make topics-create

# Verify topics exist
make topics-list

# Check Kafka container
kubectl logs deployment/kafka -n loom-dev
```

**Pre-commit Hooks Failing:**
```bash
# Run hooks manually
pre-commit run --all-files

# Bypass hooks for emergency commits
git commit --no-verify -m "commit message"

# Update hook configuration
pre-commit autoupdate
```

---

**Quick Access URLs:**
- **Main API Documentation:** http://localhost:8000/docs
- **Kafka UI:** http://localhost:8081
- **Database:** `postgresql://loom:loom@localhost:5432/loom`
- **Health Checks:**
  - Ingestion API: http://localhost:8000/healthz
  - OneFileLLM: http://localhost:8080/health
  - Silero VAD: http://localhost:8001/healthz
  - Parakeet TDT: http://localhost:8002/healthz
  - MiniCPM Vision: http://localhost:8003/healthz
  - Nomic Embed: http://localhost:8004/healthz
- **Monitoring:**
  - Prometheus Metrics: http://localhost:8000/metrics
  - API Docs: http://localhost:8000/docs
  - Redoc: http://localhost:8000/redoc

**Emergency Commands:**
```bash
make dev-down  # Stop everything
make dev-up    # Start everything
make logs      # View all logs
make status    # Check all services
```
