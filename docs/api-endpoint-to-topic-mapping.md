# API Endpoint to Kafka Topic Mapping

## Overview

This document describes the mapping between FastAPI ingestion endpoints and Kafka topics in the Loom v2 system. The mapping is now stored in the database table `topic_api_endpoints` for centralized management.

## Database Schema

### Table: `topic_api_endpoints`

Stores the many-to-many relationship between API endpoints and Kafka topics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Primary key |
| `topic_name` | TEXT | References `kafka_topics(topic_name)` |
| `api_endpoint` | TEXT | The API endpoint path (e.g., `/audio/upload`) |
| `api_method` | TEXT | HTTP method (POST, WebSocket, etc.) |
| `api_description` | TEXT | Description of what the endpoint does |
| `is_primary` | BOOLEAN | Indicates if this is the primary endpoint for the topic |

## API Services Overview

The ingestion API is organized into the following router services:

| Service | Endpoint Prefix | Topic Count | Description |
|---------|----------------|-------------|-------------|
| **audio** | `/audio/*` | 1 | Audio data ingestion (upload and streaming) |
| **sensor** | `/sensor/*` | 9 | All sensor data (GPS, accelerometer, etc.) |
| **health** | `/health/*` | 2 | Health-related data (heart rate, steps) |
| **os-events** | `/os-events/*` | 3 | Operating system events |
| **system** | `/system/*` | 3 | System monitoring and metadata |
| **images** | `/images/*` | 3 | Image and screenshot uploads |
| **digital** | `/digital/*` | 2 | Digital data (clipboard, web analytics) |
| **ingest** | `/ingest` | 7 | Unified ingestion endpoint |

## Primary Endpoint Mappings

### Audio Data
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `device.audio.raw` | `/audio/upload` | POST | Upload audio chunks in base64 format |
| | `/audio/stream/{device_id}` | WebSocket | Real-time audio streaming |

### Sensor Data
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `device.sensor.gps.raw` | `/sensor/gps` | POST | GPS coordinates with accuracy |
| `device.sensor.accelerometer.raw` | `/sensor/accelerometer` | POST | 3-axis motion data |
| `device.sensor.barometer.raw` | `/sensor/barometer` | POST | Atmospheric pressure |
| `device.sensor.temperature.raw` | `/sensor/temperature` | POST | Temperature readings |
| `device.network.wifi.raw` | `/sensor/wifi` | POST | WiFi connection state |
| `device.network.bluetooth.raw` | `/sensor/bluetooth` | POST | Bluetooth devices |
| `device.state.power.raw` | `/sensor/power` | POST | Battery level and charging |

**Batch Endpoint**: `/sensor/batch` can send to GPS, accelerometer, barometer, and temperature topics.

### Health Data
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `device.health.heartrate.raw` | `/sensor/heartrate` | POST | Heart rate measurements |
| `device.health.steps.raw` | `/sensor/steps` | POST | Step count data |

### OS Events
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `os.events.app_lifecycle.raw` | `/os-events/app-lifecycle` | POST | App lifecycle events |
| `os.events.system.raw` | `/os-events/system` | POST | System events (screen, lock, power) |
| `os.events.notifications.raw` | `/os-events/notifications` | POST | System notifications |

### System Monitoring
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `device.system.apps.android.raw` | `/system/apps/android` | POST | Android app monitoring |
| | `/system/apps/android/usage` | POST | Android usage statistics |
| `device.system.apps.macos.raw` | `/system/apps/macos` | POST | macOS app monitoring |
| `device.metadata.raw` | `/system/metadata` | POST | Device metadata |

### Media Data
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `device.image.camera.raw` | `/images/upload` | POST | Camera photos |
| `device.image.screenshot.raw` | `/images/screenshot` | POST | Screenshots |
| `device.video.screen.raw` | `/images/upload` | POST | Screen recording keyframes |

### Digital Data
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `digital.clipboard.raw` | `/digital/clipboard` | POST | Clipboard content |
| `digital.web_analytics.raw` | `/digital/web-analytics` | POST | Web analytics |
| `digital.notes.raw` | `/notes/upload` | POST | Notes and text documents |
| `digital.documents.raw` | `/documents/upload` | POST | Various document types |

### Task Processing
| Topic | Primary Endpoint | Method | Description |
|-------|-----------------|--------|-------------|
| `task.url.ingest` | `/urls/submit` | POST | Submit URLs for processing |

## Unified Ingestion Endpoint

The `/ingest` endpoint can route data to multiple topics based on the data type:

- `device.audio.raw` - Audio data
- `device.sensor.gps.raw` - GPS data
- `device.sensor.accelerometer.raw` - Accelerometer data
- `device.health.heartrate.raw` - Heart rate data
- `device.image.camera.raw` - Image data
- `device.system.apps.android.raw` - App monitoring
- `os.events.system.raw` - OS events

## Database Queries

### Find All Endpoints for a Topic
```sql
SELECT * FROM get_topic_endpoints('device.audio.raw');
```

### Find All Topics for an Endpoint
```sql
SELECT * FROM find_topics_by_endpoint('/sensor/batch');
```

### View All Primary Endpoints
```sql
SELECT * FROM v_topic_primary_endpoints
ORDER BY category, source, datatype;
```

### View Endpoints by Service
```sql
SELECT * FROM v_endpoints_by_service;
```

### Get API Documentation for a Topic
```sql
SELECT * FROM get_topic_api_docs('device.sensor.gps.raw');
```

## Pipeline Integration

The API endpoints feed into the data processing pipelines:

1. **Data Ingestion**: API endpoints receive data from devices
2. **Kafka Topics**: Data is published to appropriate Kafka topics
3. **Pipeline Processing**: Pipeline stages consume from these topics
4. **Storage**: Processed data is stored in TimescaleDB

### Example Flow: GPS Data
1. Mobile app sends GPS data to `/sensor/gps`
2. Data is published to `device.sensor.gps.raw` topic
3. Location enrichment pipeline consumes the data
4. Geocoding service enriches with address information
5. Results stored in `location_address_geocoded` table

## API Client Examples

### Upload Audio
```bash
curl -X POST http://localhost:8000/audio/upload \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T00:00:00Z",
    "audio_data": "base64_encoded_audio",
    "sample_rate": 16000
  }'
```

### Send GPS Data
```bash
curl -X POST http://localhost:8000/sensor/gps \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T00:00:00Z",
    "latitude": 36.1749,
    "longitude": -86.7678,
    "accuracy": 10.0
  }'
```

### Batch Sensor Upload
```bash
curl -X POST http://localhost:8000/sensor/batch \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "sensors": [
      {
        "type": "gps",
        "timestamp": "2024-01-01T00:00:00Z",
        "data": {
          "latitude": 36.1749,
          "longitude": -86.7678,
          "accuracy": 10.0
        }
      },
      {
        "type": "accelerometer",
        "timestamp": "2024-01-01T00:00:01Z",
        "data": {
          "x": 0.1,
          "y": -0.2,
          "z": 9.8
        }
      }
    ]
  }'
```

## Adding New Endpoints

To add a new API endpoint mapping:

```sql
-- Add the endpoint mapping
INSERT INTO topic_api_endpoints (
    topic_name,
    api_endpoint,
    api_method,
    api_description,
    is_primary
) VALUES (
    'device.new.sensor.raw',
    '/sensor/new-sensor',
    'POST',
    'New sensor type data ingestion',
    true
);

-- Verify the mapping
SELECT * FROM get_topic_endpoints('device.new.sensor.raw');
```

## Statistics

Current API endpoint statistics:
- **Total Unique Endpoints**: 29
- **Total Topic Mappings**: 43 (some endpoints map to multiple topics)
- **Topics with API Endpoints**: 23
- **Topics without API Endpoints**: 62 (processed/enriched topics)

## Migration Notes

This mapping was created in migration `033_add_api_endpoint_mapping.sql` which:
1. Created the `topic_api_endpoints` table
2. Populated mappings for all existing ingestion endpoints
3. Created views and functions for querying the mappings
4. Established the relationship between API endpoints and pipeline flows
