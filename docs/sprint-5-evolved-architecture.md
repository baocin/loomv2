# Sprint 5: Evolved Architecture - TimescaleDB Migration & AI Pipeline

> **Duration**: 4 weeks
> **Focus**: Architectural evolution with TimescaleDB, AI model integration, and comprehensive data pipeline

## 🎯 Sprint Goals

1. **Migrate to TimescaleDB** for optimal time-series data handling with 95% storage compression
2. **Implement AI model microservices** with Kafka consumer/producer pattern
3. **Create comprehensive database schema** with RLS, retention policies, and per-topic tables
4. **Add CronJob producer support** for scheduled data ingestion and external scraping
5. **Establish structured LLM outputs** using outlines library for deterministic processing

## 📋 Executive Summary: Evolved Architecture

The core architectural shift includes:
- **Re-adopting TimescaleDB** for high-volume time-series data with automated lifecycle management
- **Best-of-breed microservice pattern** with specialized AI models as independent Kafka consumers/producers
- **Structured LLM outputs** using dottxt-ai/outlines for reliable data processing
- **External data ingestion** via Kubernetes CronJobs and scheduled scrapers
- **CPU/GPU flexible inference** with containerized AI models

## 🎫 Sprint Backlog

### Epic 1: TimescaleDB Migration & Database Schema (Week 1-2)

#### TASK-501: TimescaleDB Migration
- **Description**: Migrate from vanilla PostgreSQL to TimescaleDB extension
- **Acceptance Criteria**:
  - TimescaleDB extension installed and configured
  - Existing data migrated without loss
  - Compression enabled for time-series tables
  - Retention policies configured per data type
- **Technical Implementation**:
  ```sql
  -- Enable TimescaleDB extension
  CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

  -- Create hypertables for each topic
  SELECT create_hypertable('device_audio_raw', 'timestamp');
  SELECT create_hypertable('device_sensor_gps_raw', 'timestamp');
  -- ... for all topics

  -- Configure compression (90-95% savings)
  ALTER TABLE device_audio_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
  );

  -- Add compression policy
  SELECT add_compression_policy('device_audio_raw', INTERVAL '7 days');
  ```
- **Estimate**: 13 story points

#### TASK-502: Comprehensive Database Schema Design
- **Description**: Create tables for all 50+ Kafka topics with RLS and retention policies
- **Acceptance Criteria**:
  - One table per Kafka topic with appropriate schema
  - Row-Level Security (RLS) implemented for multi-tenant data
  - Retention policies specific to data type (7-90 days)
  - Compression schemes optimized per topic
- **Schema Categories**:
  - **Raw Data Tables**: 36 tables for ingestion topics
  - **Processed Data Tables**: 8 tables for AI analysis results
  - **Command Tables**: 13 tables for remote control topics
- **RLS Implementation**:
  ```sql
  -- Enable RLS on all tables
  ALTER TABLE device_audio_raw ENABLE ROW LEVEL SECURITY;

  -- Create policies for device-based access
  CREATE POLICY device_access_policy ON device_audio_raw
    FOR ALL TO application_role
    USING (device_id = current_setting('app.current_device_id', true));
  ```
- **Estimate**: 21 story points

### Epic 2: AI Model Microservices Pipeline (Week 2-3)

#### TASK-503: Silero VAD Service
- **Description**: Voice Activity Detection microservice
- **Acceptance Criteria**:
  - Containerized Python service with torch.hub
  - Consumes from `device.audio.raw`
  - Produces to `media.audio.vad_filtered`
  - CPU-optimized with configurable thresholds
- **Implementation**:
  ```python
  # Kafka consumer/producer with structured processing
  @dataclass
  class VADResult:
      device_id: str
      timestamp: datetime
      has_speech: bool
      confidence: float
      audio_segment: bytes
  ```
- **Estimate**: 8 story points

#### TASK-504: MiniCPM Vision-Language Service
- **Description**: Vision analysis and OCR microservice
- **Acceptance Criteria**:
  - HuggingFace transformers + outlines integration
  - Consumes from `device.image.camera.raw`, `device.video.screen.raw`
  - Produces structured JSON to `media.image.analysis.minicpm_results`
  - GPU-preferred, CPU-viable deployment
- **Structured Output Schema**:
  ```python
  class VisionAnalysisResult(BaseModel):
      objects_detected: List[str]
      text_extracted: str
      scene_description: str
      confidence_scores: Dict[str, float]
  ```
- **Estimate**: 13 story points

#### TASK-505: Mistral Reasoning Service
- **Description**: High-level context inference service
- **Acceptance Criteria**:
  - Ollama server integration with outlines
  - Consumes from multiple text topics
  - Produces to `analysis.inferred_context.mistral_results`
  - Structured reasoning outputs
- **Estimate**: 13 story points

### Epic 3: CronJob Producer Support (Week 3)

#### TASK-506: Kubernetes CronJob Framework
- **Description**: Generic framework for scheduled data producers
- **Acceptance Criteria**:
  - Base CronJob Helm chart template
  - Configurable scheduling (cron expressions)
  - Kafka producer integration
  - Error handling and retry logic
  - Monitoring and alerting
- **CronJob Types**:
  - External URL scraping
  - Health check data collection
  - System metric gathering
  - Data export/backup jobs
- **Estimate**: 8 story points

#### TASK-507: External Data Scrapers
- **Description**: Scheduled scrapers for external data sources
- **Acceptance Criteria**:
  - Twitter/X scraper producing to `external.twitter.liked.raw`
  - Calendar events scraper for `external.calendar.events.raw`
  - Email events scraper for `external.email.events.raw`
  - Generic URL processor for `task.url.ingest`
- **Implementation Pattern**:
  ```python
  # CronJob produces simple messages
  @dataclass
  class URLIngestTask:
      url: str
      scrape_type: str
      priority: int
      metadata: Dict[str, Any]

  # Dedicated consumer processes URLs
  class URLProcessor:
      async def process_url(self, task: URLIngestTask) -> ProcessedContent
  ```
- **Estimate**: 13 story points

### Epic 4: Remote Control Infrastructure (Week 4)

#### TASK-508: Bidirectional Kafka Topics
- **Description**: Implement command/response pattern for remote device control
- **Acceptance Criteria**:
  - 13 command topics for device control
  - 5 response topics for status/results
  - 3 sync topics for cross-device communication
  - Message correlation and timeout handling
- **Command Pattern**:
  ```python
  @dataclass
  class DeviceCommand:
      command_id: str
      target_device_id: str
      command_type: str
      payload: Dict[str, Any]
      timeout_seconds: int = 30

  @dataclass
  class DeviceResponse:
      command_id: str
      device_id: str
      status: str  # success, error, timeout
      result: Optional[Dict[str, Any]]
      error_message: Optional[str]
  ```
- **Estimate**: 13 story points

## 📊 Database Schema Specifications

### Table Design per Kafka Topic

#### Raw Data Tables (36 tables)
```sql
-- Audio data (7 days retention, high compression)
CREATE TABLE device_audio_raw (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data BYTEA NOT NULL,
    format VARCHAR(50) NOT NULL,
    sample_rate INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- GPS data (30 days retention, moderate compression)
CREATE TABLE device_sensor_gps_raw (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    accuracy DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Heart rate data (60 days retention, low compression)
CREATE TABLE device_health_heartrate_raw (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    heart_rate INTEGER NOT NULL,
    confidence DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Processed Data Tables (8 tables)
```sql
-- Vision analysis results (90 days retention)
CREATE TABLE media_image_analysis_minicpm_results (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    source_image_id VARCHAR(255),
    objects_detected JSONB,
    text_extracted TEXT,
    scene_description TEXT,
    confidence_scores JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Context inference results (180 days retention)
CREATE TABLE analysis_inferred_context_mistral_results (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(255),
    timestamp TIMESTAMPTZ NOT NULL,
    input_sources JSONB,
    context_type VARCHAR(100),
    inferred_context JSONB,
    confidence_score DOUBLE PRECISION,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Command Tables (13 tables)
```sql
-- Device commands (30 days retention)
CREATE TABLE device_command_keystroke_send (
    id BIGSERIAL PRIMARY KEY,
    command_id VARCHAR(255) UNIQUE NOT NULL,
    source_device_id VARCHAR(255) NOT NULL,
    target_device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    keystrokes JSONB NOT NULL,
    modifiers JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Command responses (30 days retention)
CREATE TABLE device_response_command_status (
    id BIGSERIAL PRIMARY KEY,
    command_id VARCHAR(255) NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL,
    result JSONB,
    error_message TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Retention Policies per Topic Category

```sql
-- Audio data: 7 days retention, daily compression
SELECT add_retention_policy('device_audio_raw', INTERVAL '7 days');
SELECT add_compression_policy('device_audio_raw', INTERVAL '1 day');

-- Sensor data: 30 days retention, weekly compression
SELECT add_retention_policy('device_sensor_gps_raw', INTERVAL '30 days');
SELECT add_compression_policy('device_sensor_gps_raw', INTERVAL '7 days');

-- Health data: 60 days retention, weekly compression
SELECT add_retention_policy('device_health_heartrate_raw', INTERVAL '60 days');
SELECT add_compression_policy('device_health_heartrate_raw', INTERVAL '7 days');

-- Analysis results: 90-180 days retention, monthly compression
SELECT add_retention_policy('analysis_inferred_context_mistral_results', INTERVAL '180 days');
SELECT add_compression_policy('analysis_inferred_context_mistral_results', INTERVAL '30 days');

-- Command data: 30 days retention, weekly compression
SELECT add_retention_policy('device_command_keystroke_send', INTERVAL '30 days');
SELECT add_compression_policy('device_command_keystroke_send', INTERVAL '7 days');
```

### Row-Level Security Implementation

```sql
-- Create application roles
CREATE ROLE device_owner;
CREATE ROLE device_admin;
CREATE ROLE data_analyst;

-- Enable RLS on all tables
DO $$
DECLARE
    tbl record;
BEGIN
    FOR tbl IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl.tablename);
    END LOOP;
END
$$;

-- Device owner can only access their own data
CREATE POLICY device_owner_policy ON device_audio_raw
    FOR ALL TO device_owner
    USING (device_id = current_setting('app.current_device_id', true));

-- Admin can access all data
CREATE POLICY admin_policy ON device_audio_raw
    FOR ALL TO device_admin
    USING (true);

-- Analyst can read all data but not modify
CREATE POLICY analyst_policy ON device_audio_raw
    FOR SELECT TO data_analyst
    USING (true);
```

## 🔧 Configuration Changes

### New Environment Variables
```bash
# TimescaleDB Configuration
export LOOM_DATABASE_URL="postgresql://loom:loom@localhost:5432/loom"
export LOOM_TIMESCALEDB_ENABLED=true
export LOOM_COMPRESSION_ENABLED=true
export LOOM_DEFAULT_RETENTION_DAYS=30

# AI Model Services
export LOOM_AI_SERVICES_ENABLED=true
export LOOM_GPU_ACCELERATION=true
export LOOM_SILERO_VAD_THRESHOLD=0.5
export LOOM_MINICPM_GPU_MEMORY_LIMIT="8Gi"
export LOOM_MISTRAL_OLLAMA_SERVER="http://ollama:11434"

# CronJob Configuration
export LOOM_CRONJOBS_ENABLED=true
export LOOM_SCRAPER_SCHEDULE="0 */6 * * *"  # Every 6 hours
export LOOM_EXTERNAL_SCRAPING_ENABLED=true

# Remote Control
export LOOM_REMOTE_CONTROL_ENABLED=true
export LOOM_COMMAND_TIMEOUT_SECONDS=30
export LOOM_CROSS_DEVICE_SYNC=true
```

## 🧪 Testing Strategy

### Database Migration Testing
- Zero-downtime migration validation
- Data integrity verification
- Performance benchmarking (compression ratios)
- Retention policy automation testing

### AI Pipeline Testing
- End-to-end data flow validation
- Model accuracy regression testing
- GPU/CPU fallback testing
- Structured output validation

### CronJob Testing
- Schedule accuracy testing
- Failure recovery and retry logic
- External API integration testing
- Data consistency validation

## 📈 Success Metrics

### Performance Targets
- **Storage Compression**: 90-95% reduction in storage usage
- **Query Performance**: 10x faster time-range queries
- **AI Processing**: <2 seconds average latency per model
- **CronJob Reliability**: 99.9% successful execution rate

### Functional Goals
- ✅ All 57 Kafka topics have corresponding database tables
- ✅ RLS policies protect multi-tenant data access
- ✅ Retention policies automatically manage data lifecycle
- ✅ AI models produce structured, validated outputs
- ✅ CronJobs reliably ingest external data sources

## 🚀 Deployment Plan

### Week 1: Database Foundation
1. Deploy TimescaleDB in development
2. Create comprehensive table schemas
3. Implement RLS policies
4. Configure retention and compression

### Week 2: AI Model Services
1. Deploy Silero VAD service
2. Deploy MiniCPM vision service
3. Deploy Mistral reasoning service
4. Configure GPU/CPU node selection

### Week 3: CronJob Infrastructure
1. Deploy CronJob framework
2. Implement external scrapers
3. Configure scheduling and monitoring
4. Test failure recovery

### Week 4: Remote Control & Integration
1. Deploy bidirectional command system
2. Implement cross-device sync
3. End-to-end integration testing
4. Performance optimization

## 🔗 Dependencies

### Infrastructure
- **TimescaleDB**: PostgreSQL extension for time-series data
- **GPU Nodes**: NVIDIA GPU support for AI models
- **Kubernetes**: CronJob and node selector support
- **Helm Charts**: Updated charts for new services

### Libraries
- **dottxt-ai/outlines**: Structured LLM output generation
- **torch**: PyTorch for Silero VAD
- **transformers**: HuggingFace model integration
- **aiokafka**: Enhanced admin client for topic management
- **ollama**: Local LLM inference server

---

**Sprint Start**: 2024-07-06
**Sprint End**: 2024-08-03
**Sprint Master**: Architecture Team
**Product Owner**: AI Platform Team
