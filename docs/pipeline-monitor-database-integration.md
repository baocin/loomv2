# Pipeline Monitor Database Integration

## Overview

The Pipeline Monitor API now loads pipeline definitions directly from the TimescaleDB database instead of hardcoded mappings. This provides dynamic, real-time pipeline visualization based on the actual configuration stored in the database.

## Architecture Changes

### Previous Architecture
- Pipeline definitions hardcoded in `pipelineBuilder.ts`
- Manual mapping of consumer groups to topics
- Static producer and consumer definitions
- Limited to known services

### New Architecture
- Pipeline definitions loaded from database tables
- Dynamic discovery of flows, stages, and topics
- Automatic API endpoint mapping
- Service dependency tracking
- Complete data lineage visualization

## Database Tables Used

### Core Pipeline Tables
1. **pipeline_flows** - High-level pipeline definitions
2. **pipeline_stages** - Individual processing stages within flows
3. **pipeline_stage_topics** - Topic relationships (input/output/error)
4. **kafka_topics** - Topic metadata and configuration
5. **topic_api_endpoints** - API endpoint to topic mappings
6. **topic_table_configs** - Topic to database table mappings

## New API Endpoints

### Pipeline Routes (`/api/pipelines`)

#### Get All Pipeline Flows
```bash
GET /api/pipelines/flows
```
Returns all active pipeline flows with stage and topic counts.

#### Get Pipeline Stages
```bash
GET /api/pipelines/stages
GET /api/pipelines/stages?flow=audio-processing
```
Returns all stages, optionally filtered by flow name.

#### Get Topic Mappings
```bash
GET /api/pipelines/topics
```
Returns all topics with their metadata, API endpoints, and storage tables.

#### Get Pipeline Topology
```bash
GET /api/pipelines/topology
```
Returns complete pipeline topology including:
- All flows
- All stages with input/output topics
- All topics with producers/consumers
- Topic producer/consumer mapping

#### Get Service Dependencies
```bash
GET /api/pipelines/dependencies
```
Returns service-to-service dependencies based on topic connections.

#### Get Flow Details
```bash
GET /api/pipelines/flows/{flowName}
```
Returns detailed information about a specific flow including all stages.

#### Get Service Pipelines
```bash
GET /api/pipelines/services/{serviceName}
```
Returns all pipeline stages that use a specific service.

#### Get Topic Lineage
```bash
GET /api/pipelines/topics/{topicName}/lineage
```
Returns complete lineage for a topic:
- Producer stages
- Consumer stages
- API endpoints
- Storage table

### Enhanced Kafka Routes

#### Database-Driven Pipeline Visualization
```bash
GET /api/kafka/pipeline/database
```
Returns pipeline structure built from database configuration.

#### Pipeline Topology
```bash
GET /api/kafka/pipeline/topology
```
Returns raw topology data from database.

#### Service Dependencies
```bash
GET /api/kafka/pipeline/dependencies
```
Returns service dependency graph.

## Pipeline Builder Updates

### New Method: `buildPipelineFromDatabase()`
- Loads pipeline configuration from database
- Creates nodes for:
  - API endpoints (producers)
  - Kafka topics (grouped by stage)
  - Processing services (from pipeline stages)
  - TimescaleDB (storage)
- Automatically connects nodes based on relationships

### Fallback Behavior
The pipeline builder now:
1. First attempts to load from database
2. Falls back to discovery-based method if database fails
3. Provides seamless transition between methods

## Data Flow Visualization

### Node Types
1. **External** - API endpoints that produce data
2. **Kafka Topic** - Message topics (raw, processed, analysis)
3. **Processor** - Services that consume and produce data
4. **Database** - TimescaleDB storage

### Edge Connections
- API endpoints → Raw topics
- Raw topics → Processors
- Processors → Processed topics
- Topics with table mappings → Database

## Example Usage

### Get Complete Pipeline View
```bash
# Get database-driven pipeline
curl http://localhost:8003/api/kafka/pipeline/database

# Response includes nodes and edges for visualization
{
  "nodes": [
    {
      "id": "api-/audio/upload",
      "type": "external",
      "position": { "x": 0, "y": 100 },
      "data": {
        "label": "/audio/upload",
        "status": "active",
        "description": "API Endpoint"
      }
    },
    ...
  ],
  "edges": [
    {
      "id": "e-api-/audio/upload-device.audio.raw",
      "source": "api-/audio/upload",
      "target": "device.audio.raw",
      "animated": true
    },
    ...
  ]
}
```

### Get Audio Processing Flow
```bash
curl http://localhost:8003/api/pipelines/flows/audio-processing

# Response
{
  "flow": {
    "flow_name": "audio-processing",
    "description": "Audio data processing pipeline",
    "priority": "high",
    "stage_count": 2
  },
  "stages": [
    {
      "stage_name": "vad-processing",
      "service_name": "silero-vad",
      "input_topics": ["device.audio.raw"],
      "output_topics": ["media.audio.vad_filtered"]
    },
    {
      "stage_name": "speech-to-text",
      "service_name": "kyutai-stt",
      "input_topics": ["device.audio.raw"],
      "output_topics": ["media.text.transcribed.words"]
    }
  ]
}
```

### Get Topic Lineage
```bash
curl http://localhost:8003/api/pipelines/topics/device.audio.raw/lineage

# Response
{
  "topic": {
    "topic_name": "device.audio.raw",
    "description": "Raw microphone audio chunks",
    "retention_days": 7,
    "primary_endpoints": ["/audio/upload", "/audio/stream/{device_id}"],
    "table_name": "device_audio_raw"
  },
  "producers": [],
  "consumers": [
    {
      "flow": "audio-processing",
      "stage": "vad-processing",
      "service": "silero-vad"
    },
    {
      "flow": "audio-processing",
      "stage": "speech-to-text",
      "service": "kyutai-stt"
    }
  ],
  "apiEndpoints": ["/audio/upload", "/audio/stream/{device_id}"],
  "storageTable": "device_audio_raw"
}
```

## Benefits

1. **Dynamic Configuration** - Pipeline changes are reflected immediately
2. **Complete Visibility** - See all flows, stages, and connections
3. **API Integration** - Understand data flow from API to storage
4. **Service Dependencies** - Track inter-service communication
5. **Topic Lineage** - Full producer/consumer tracking
6. **No Code Changes** - Add new flows without modifying monitor code

## Migration Notes

To use the database-driven pipeline monitor:

1. Ensure all pipeline flows are imported to database:
   ```bash
   cd scripts
   python import_kafka_schemas.py
   ```

2. Verify flows are loaded:
   ```bash
   curl http://localhost:8003/api/pipelines/flows
   ```

3. Switch to database-driven visualization:
   ```bash
   # Instead of: /api/kafka/pipeline
   # Use: /api/kafka/pipeline/database
   ```

## Future Enhancements

1. **Real-time Updates** - WebSocket updates when pipeline config changes
2. **Health Integration** - Show service health on pipeline nodes
3. **Metrics Overlay** - Display throughput/lag on edges
4. **Interactive Editing** - Modify pipeline configuration from UI
5. **Version History** - Track pipeline configuration changes
