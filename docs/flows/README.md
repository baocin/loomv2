# Loom v2 Data Processing Flows

This directory contains the detailed specifications for all data processing pipelines in Loom v2. Each flow is defined as a series of stages that transform raw data into enriched, analyzed, and persisted information.

## Flow Architecture

### Design Principles

1. **Microservice-per-Stage**: Each processing stage runs as an independent microservice
2. **Kafka-Centric**: All inter-service communication happens through Kafka topics
3. **Schema-Driven**: Every stage has defined input/output schemas
4. **Failure Resilient**: Built-in retry policies and error handling
5. **Observable**: Comprehensive monitoring and alerting

### Runtime Configuration

Services discover their configuration through environment variables:
```bash
INPUT_TOPICS=device.audio.raw
OUTPUT_TOPICS=media.audio.vad_filtered
ERROR_TOPIC=processing.errors.vad
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
DATABASE_URL=postgresql://loom:loom@postgres:5432/loom  # Optional for services needing DB access
```

### Database Access Pattern

Many services can optionally read from the database for context enrichment:
- **Georegion Detector**: Reads saved georegion definitions
- **Business Matcher**: Queries historical visit data
- **Context Services**: Access user preferences and patterns

This hybrid approach allows services to:
1. Process streaming data from Kafka (primary data flow)
2. Enrich with database context when needed (secondary lookups)
3. Write results back to Kafka for downstream processing

## Processing Flows

### 1. Audio Processing
**File**: `audio-processing.yaml`
- **Priority**: Critical
- **Stages**: VAD → Speech-to-Text → Environment Classification → Database
- **Key Models**: Silero VAD, NVIDIA Parakeet-TDT
- **Data Volume**: ~10 events/second

### 2. Location Enrichment
**File**: `location-enrichment.yaml`
- **Priority**: High
- **Stages**: Geocoding → Business Identification → Database
- **Key Services**: Nominatim, Foursquare/Google Places
- **Data Volume**: ~0.1 events/second

### 3. App Lifecycle
**File**: `app-lifecycle.yaml`
- **Priority**: High
- **Stages**: Event Enrichment → Database
- **Key Features**: App categorization, session tracking
- **Data Volume**: ~2 events/second

### 4. Motion Classification
**File**: `motion-classification.yaml`
- **Priority**: Medium
- **Stages**: Aggregation → Motion Detection → Activity Classification → Database
- **Key Models**: TensorFlow Activity Recognition
- **Data Volume**: ~50 events/second

### 5. Screenshot OCR
**File**: `screenshot-ocr.yaml`
- **Priority**: High
- **Stages**: Preprocessing → OCR → Text Cleaning → Database
- **Key Tools**: Tesseract OCR
- **Data Volume**: ~0.1 events/second

### 6. Email Processing
**File**: `email-processing.yaml`
- **Priority**: Medium
- **Stages**: Fetching → Parsing → Embedding → Database
- **Key Models**: Sentence Transformers
- **Data Volume**: ~0.01 events/second

### 7. Calendar Processing
**File**: `calendar-processing.yaml`
- **Priority**: Medium
- **Stages**: Fetching → Enrichment → Embedding → Database
- **Key Features**: Meeting type classification
- **Data Volume**: ~0.001 events/second

### 8. Hacker News Processing
**File**: `hackernews-processing.yaml`
- **Priority**: Low
- **Stages**: Scraping → Content Fetching → Embedding → Database
- **Key Features**: Full article extraction
- **Data Volume**: ~0.0001 events/second

### 9. Camera Vision
**File**: `camera-vision.yaml`
- **Priority**: High
- **Stages**: Object Detection → Face/Pose/Gaze → SLAM → Database
- **Key Models**: Moondream, MediaPipe, ORB-SLAM3
- **Data Volume**: ~0.03 events/second

### 10. Power State
**File**: `power-state.yaml`
- **Priority**: Medium
- **Stages**: Enrichment → Pattern Detection → Database
- **Key Features**: Charging patterns, battery health
- **Data Volume**: ~0.1 events/second

### 11. Network Events
**File**: `network-events.yaml`
- **Priority**: Low
- **Stages**: Enrichment → Location Correlation → Database
- **Key Features**: Network categorization
- **Data Volume**: ~0.01 events/second

## Kafka Topic Naming Convention

All topics follow the pattern: `<category>.<source>.<datatype>.<stage>`

### Categories:
- `device` - Data from user devices
- `media` - Processed media content
- `os` - Operating system events
- `external` - Third-party data sources
- `location` - Geographic information
- `motion` - Movement and activity data
- `spatial` - 3D/spatial data
- `processing` - System processing topics

### Common Stages:
- `raw` - Unprocessed input data
- `filtered` - Basic filtering applied
- `enriched` - Additional metadata added
- `embedded` - Vector embeddings generated
- `classified` - ML classification applied
- `detected` - Detection results

## Database Integration

All flows terminate in a TimescaleDB writer service that:
- Batches writes for efficiency
- Handles schema evolution
- Manages time-series compression
- Implements retention policies

### Hypertable Configuration
```yaml
hypertable_config:
  time_column: timestamp
  chunk_time_interval: 1 day
  compression_after: 7 days
  retention_days: 30
```

## Monitoring and Alerting

Each stage defines:
- **SLA**: Expected processing time per event
- **Error Rate Threshold**: When to trigger alerts
- **Prometheus Metrics**: Custom metrics per service

### Key Metrics
- `processing_latency_seconds{service, stage}`
- `events_processed_total{service, topic}`
- `errors_total{service, error_type}`
- `batch_size_histogram{service}`

## Development Guidelines

### Adding a New Flow

1. Create a new YAML file following the schema in `_schema.yaml`
2. Define all stages with clear responsibilities
3. Specify data volumes and performance requirements
4. Include monitoring and error handling
5. Update this README with the flow summary

### Service Implementation

Each service should:
1. Read configuration from environment variables
2. Implement health checks (`/healthz`, `/readyz`)
3. Export Prometheus metrics
4. Handle graceful shutdown
5. Log structured JSON with correlation IDs

### Testing Flows

1. Unit test each service independently
2. Integration test with local Kafka
3. Load test with expected data volumes
4. Chaos test with service failures
5. Monitor resource usage

## Schema Evolution

- Minor versions (v1.1, v1.2) must be backward compatible
- Major versions (v2.0) can break compatibility
- Services should handle multiple schema versions
- Use schema registry for production

## Performance Considerations

### Batching Strategy
- Small batches (1-5) for low-latency flows
- Large batches (50-500) for high-volume flows
- Time-based flushing for low-frequency data

### Resource Allocation
- CPU-bound services: More replicas
- GPU services: Vertical scaling
- I/O-bound services: Optimize batching

### Kafka Optimization
- Compression: LZ4 for high-volume topics
- Partitioning: Based on device_id or user_id
- Retention: Match database retention policies