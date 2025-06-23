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
curl -H "X-API-Key: pineapple" http://localhost:8000/audio/upload
```

### Audio Endpoints

**Upload Audio Chunk:**
```bash
curl -X POST http://localhost:8000/audio/upload \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
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
  -H "X-API-Key: pineapple" \
  -d '{
    "device_id": "12345678-1234-1234-1234-123456789012",
    "recorded_at": "2024-01-23T10:30:00Z",
    "title": "My Note",
    "content": "# Header\n\nThis is **bold** text with a [link](https://example.com).",
    "note_type": "markdown",
    "tags": ["work", "important"]
  }'
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
| `/notes/upload` | `device.text.notes.raw` | Text notes/memos |

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
- API Documentation: http://localhost:8000/docs
- Kafka UI: http://localhost:8081
- Database: `postgresql://loom:loom@localhost:5432/loom`
- Health Check: http://localhost:8000/healthz
- Metrics: http://localhost:8000/metrics

**Emergency Commands:**
```bash
make dev-down  # Stop everything
make dev-up    # Start everything
make logs      # View all logs
make status    # Check all services
```
