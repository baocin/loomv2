# Unified Data Ingestion API

## Overview

The unified ingestion API simplifies data ingestion by using a single endpoint with message type IDs that map directly to Kafka topics. Kafka's native routing capabilities (consumer groups) handle message distribution to multiple consumers.

## Key Benefits

1. **Single Endpoint**: `/ingest/message` handles all data types
2. **Simple Topic Mapping**: Each `message_type_id` maps to an entry point Kafka topic
3. **Kafka-Native Routing**: Consumer groups handle duplication and load balancing
4. **Fixed Screenshot Pipeline**: Twitter screenshots route to OCR, general screenshots to storage
5. **Pipeline Hints**: Optional hints help consumers understand processing intent
6. **Automatic Validation**: Built-in validation rules for each message type

## Usage

### Basic Request Format

```json
POST /ingest/message
{
    "message_type_id": "twitter_screenshot",
    "device_id": "device-uuid-here",
    "data": {
        "image_data": "base64-encoded-image-data",
        "width": 1920,
        "height": 1080,
        "format": "png"
    },
    "metadata": {
        "app_name": "Twitter",
        "window_title": "Tweet thread"
    }
}
```

### Response Format

```json
{
    "status": "success",
    "message_type": "twitter_screenshot", 
    "topic": "external.twitter.images.raw",
    "timestamp": "2025-07-02T20:45:00Z"
}
```

### Message Structure in Kafka

Messages sent to Kafka include pipeline hints when applicable:

```json
{
    "schema_version": "1.0",
    "device_id": "device-uuid-here",
    "message_type": "twitter_screenshot",
    "pipeline_hint": "ocr_extraction",  // Added for pipeline-aware messages
    "data": {
        "image_data": "base64-encoded-image-data",
        "width": 1920,
        "height": 1080
    },
    "metadata": {
        "app_name": "Twitter"
    },
    "timestamp": "2025-07-02T20:45:00Z"
}
```

## Message Types and Kafka Topic Mapping

### Image/Video Types
- `screenshot` → `device.video.screen.raw` (general screenshots, direct storage)
- `twitter_screenshot` → `external.twitter.images.raw` (Twitter/X screenshots for OCR processing)
- `camera_photo` → `device.image.camera.raw` (photos from device camera)

### Sensor Data
- `gps_reading` → `device.sensor.gps.raw`
- `accelerometer` → `device.sensor.accelerometer.raw`
- `heartrate` → `device.health.heartrate.raw`
- `power_state` → `device.state.power.raw`
- `temperature` → `device.sensor.temperature.raw`
- `barometer` → `device.sensor.barometer.raw`

### Network Data
- `wifi_state` → `device.network.wifi.raw`
- `bluetooth_scan` → `device.network.bluetooth.raw`

### OS Events
- `app_lifecycle` → `os.events.app_lifecycle.raw`
- `system_event` → `os.events.system.raw`
- `notification` → `os.events.notifications.raw`

### System Monitoring
- `macos_apps` → `device.system.apps.macos.raw`
- `android_apps` → `device.system.apps.android.raw`
- `device_metadata` → `device.metadata.raw`

### Digital Content
- `digital_note` → `digital.notes.raw`
- `clipboard` → `digital.clipboard.raw`

### Audio
- `audio_chunk` → `device.audio.raw`

### External Sources
- `twitter_liked` → `external.twitter.liked.raw`
- `email_event` → `external.email.events.raw`
- `calendar_event` → `external.calendar.events.raw`

### Tasks
- `url_to_process` → `task.url.ingest`

## Kafka-Based Routing and Processing

### How Routing Works

Kafka uses **consumer groups** to handle message distribution:

1. **Different Consumer Groups = Message Duplication**
   - Each consumer group receives ALL messages from a topic
   - Example: Both Moondream OCR and MiniCPM OCR can process the same images

2. **Same Consumer Group = Load Balancing**
   - Messages are distributed among consumers in the same group
   - Example: Multiple Moondream instances can share the workload

### Screenshot Processing Examples

#### General Screenshots (Direct Storage)
```
Mobile App → [screenshot] → device.video.screen.raw → Database
```

#### Twitter Screenshots (OCR Processing)
```
Mobile App → [twitter_screenshot] → external.twitter.images.raw → Moondream OCR → media.image.analysis.moondream_results → Database
```

### Example Mobile App Usage

```dart
// Flutter/Dart example - Twitter screenshot for OCR
final response = await http.post(
  Uri.parse('$apiUrl/ingest/message'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'message_type_id': 'twitter_screenshot',  // Routes to OCR pipeline
    'device_id': deviceId,
    'data': {
      'image_data': base64Image,
      'width': imageWidth,
      'height': imageHeight,
      'format': 'png',
    },
    'metadata': {
      'app_name': 'Twitter',
      'timestamp': DateTime.now().toIso8601String(),
    }
  }),
);

// General screenshot - no OCR needed
final response = await http.post(
  Uri.parse('$apiUrl/ingest/message'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'message_type_id': 'screenshot',  // Direct to storage
    'device_id': deviceId,
    'data': {
      'image_data': base64Image,
      'width': imageWidth,
      'height': imageHeight,
      'format': 'png',
    }
  }),
);
```

## Validation Rules

Each message type has specific validation rules:

### Image Types (screenshot, twitter_screenshot, camera_photo)
- **Required fields**: `image_data`, `width`, `height`
- **Base64 validation**: `image_data` must be valid base64

### Audio Types (audio_chunk)
- **Required fields**: `chunk_data`, `sample_rate`, `duration_ms`
- **Base64 validation**: `chunk_data` must be valid base64

### GPS Types (gps_reading)
- **Required fields**: `latitude`, `longitude`

### Accelerometer Types (accelerometer)
- **Required fields**: `x`, `y`, `z`

## Discovery Endpoints

### Get All Message Types
```bash
GET /ingest/message-types
```

Returns mapping of all message type IDs to their Kafka topics.

### Get Specific Message Type Info
```bash
GET /ingest/message-types/twitter_screenshot
```

Returns detailed information about a specific message type including validation rules and pipeline hints:

```json
{
    "message_type_id": "twitter_screenshot",
    "topic": "external.twitter.images.raw",
    "pipeline_hint": "ocr_extraction",
    "validation_rules": {
        "required_fields": ["image_data", "width", "height"],
        "validate_base64": ["image_data"]
    }
}
```

## Migration from Existing Endpoints

### Old Way (Multiple Endpoints)
```json
POST /images/screenshot
{
    "device_id": "device-uuid",
    "image_data": "base64-data",
    "width": 1920,
    "height": 1080,
    "format": "png",
    "camera_type": "screen"
}
```

### New Way (Unified Endpoint)
```json
POST /ingest/message
{
    "message_type_id": "twitter_screenshot",  // or "screenshot" for general
    "device_id": "device-uuid", 
    "data": {
        "image_data": "base64-data",
        "width": 1920,
        "height": 1080,
        "format": "png"
    }
}
```

## Benefits for Mobile Development

1. **Single Integration**: Mobile apps only need to implement one API endpoint
2. **Type Safety**: Message types are predefined and validated
3. **Future Proof**: New data types can be added without changing mobile code
4. **Simplified Routing**: No need to know which specific endpoint to use
5. **Better Error Messages**: Clear validation errors for each message type

## Backwards Compatibility

The existing endpoints (`/images/screenshot`, `/sensor/gps`, etc.) remain functional. The unified API is additive and provides an alternative, simpler way to ingest data.