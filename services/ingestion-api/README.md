# Ingestion API Service

Core data ingestion service for Loom v2 that provides REST and WebSocket endpoints for device data.

## Features

- REST API for comprehensive data ingestion (sensors, health, images, documents, system monitoring)
- WebSocket support for real-time audio streaming
- Schema validation using JSON Schema
- Automatic Kafka topic publishing with trace context
- Health check and metrics endpoints (Prometheus)
- Unified ingestion endpoint with automatic message routing
- Database migrations for PostgreSQL/TimescaleDB

## API Endpoints

### Health & Monitoring
- `GET /` - Service information and endpoint listing
- `GET /healthz` - Kubernetes liveness probe
- `GET /readyz` - Kubernetes readiness probe with dependency checks
- `GET /metrics` - Prometheus metrics endpoint

### Audio Data
- `POST /audio/upload` - Upload audio chunks
- `WebSocket /audio/stream/{device_id}` - Real-time audio streaming

### Sensor Data
- `POST /sensor/gps` - GPS coordinates with accuracy
- `POST /sensor/accelerometer` - 3-axis motion data
- `POST /sensor/heartrate` - Heart rate measurements
- `POST /sensor/power` - Device power state
- `POST /sensor/temperature` - Temperature readings
- `POST /sensor/barometer` - Barometric pressure
- `POST /sensor/light` - Ambient light sensor
- `POST /sensor/gyroscope` - Gyroscope readings
- `POST /sensor/magnetometer` - Magnetic field data
- `POST /sensor/wifi` - WiFi network information
- `POST /sensor/bluetooth` - Bluetooth device discovery
- `POST /sensor/batch` - Batch upload multiple sensor readings

### Health Monitoring
- `POST /health/steps` - Step count data
- `POST /health/sleep` - Sleep tracking data
- `POST /health/blood-pressure` - Blood pressure measurements

### OS Events
- `POST /os-events/app-lifecycle` - Application lifecycle events
- `POST /os-events/system` - System events (screen, lock, power)
- `POST /os-events/notifications` - Notification events
- `GET /os-events/event-types` - List supported event types

### System Monitoring
- `POST /system/apps/android` - Android app monitoring data
- `POST /system/apps/android/usage` - Android app usage statistics
- `POST /system/apps/android/events` - Individual Android app events
- `POST /system/apps/android/categories` - App category statistics
- `POST /system/apps/macos` - macOS app monitoring data
- `POST /system/metadata` - Device metadata and capabilities
- `GET /system/apps/stats` - App monitoring statistics
- `POST /meta/consumer_activity` - Consumer activity logging
- `GET /meta/consumer_activity` - Get consumer monitoring data

### Digital Data
- `POST /digital/clipboard` - Clipboard content
- `POST /digital/web-analytics` - Web analytics data

### Documents & Notes
- `POST /documents/text` - Text document ingestion
- `POST /documents/markdown` - Markdown document ingestion
- `POST /documents/pdf` - PDF document ingestion
- `POST /notes/text` - Plain text notes
- `POST /notes/markdown` - Markdown notes
- `POST /notes/audio` - Audio notes

### Images
- `POST /images/camera` - Camera photos
- `POST /images/screenshot` - Screenshots

### AI Context
- `POST /ai-context/inferred` - AI-inferred context data

### Unified Ingestion
- `POST /unified/ingest` - Unified endpoint with automatic message type routing

## Configuration

Environment variables (with `LOOM_` prefix):
- `LOOM_DATABASE_URL` - PostgreSQL connection string
- `LOOM_KAFKA_BOOTSTRAP_SERVERS` - Kafka broker addresses
- `LOOM_HOST` - API server host (default: 0.0.0.0)
- `LOOM_PORT` - API server port (default: 8000)
- `LOOM_LOG_LEVEL` - Logging level (default: INFO)
- `LOOM_CORS_ORIGINS` - CORS allowed origins
- `LOOM_ENVIRONMENT` - Environment (development/production)
- `LOOM_DEBUG` - Debug mode flag

See docker-compose.local.yml for complete configuration options.
