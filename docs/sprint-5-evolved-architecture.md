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

#### TASK-507: IMAP Email Sync CronJob
- **Description**: Scheduled IMAP email synchronization service
- **Acceptance Criteria**:
  - CronJob runs every 15 minutes (configurable)
  - Connects to IMAP servers (Gmail, Outlook, custom)
  - Filters emails by criteria (unread, starred, labels)
  - Produces to `external.email.events.raw` with full email content
  - Supports OAuth2 and password authentication
  - Handles attachments by uploading to object storage
- **Technical Implementation**:
  ```python
  @dataclass
  class EmailSyncJob:
      imap_server: str
      username: str
      auth_method: str  # oauth2, password
      filters: List[str]  # unread, starred, label:important
      last_sync_uid: Optional[int]
  
  @dataclass 
  class EmailEvent:
      message_id: str
      from_address: str
      to_addresses: List[str]
      subject: str
      body_text: str
      body_html: Optional[str]
      attachments: List[AttachmentRef]
      labels: List[str]
      received_date: datetime
  ```
- **Schedule**: `*/15 * * * *` (every 15 minutes)
- **Estimate**: 8 story points

#### TASK-508: Google Calendar Sync CronJob
- **Description**: Scheduled Google Calendar event synchronization
- **Acceptance Criteria**:
  - CronJob runs every 30 minutes
  - Uses Google Calendar API with OAuth2
  - Syncs events from specified calendars
  - Handles recurring events properly
  - Produces to `external.calendar.events.raw`
  - Tracks event modifications and deletions
- **Technical Implementation**:
  ```python
  @dataclass
  class CalendarSyncJob:
      calendar_ids: List[str]
      sync_window_days: int = 30  # Past and future
      include_declined: bool = False
      last_sync_token: Optional[str]
  
  @dataclass
  class CalendarEvent:
      event_id: str
      calendar_id: str
      title: str
      description: Optional[str]
      start_time: datetime
      end_time: datetime
      location: Optional[str]
      attendees: List[str]
      recurrence_rule: Optional[str]
      status: str  # confirmed, tentative, cancelled
  ```
- **Schedule**: `*/30 * * * *` (every 30 minutes)
- **Estimate**: 8 story points

#### TASK-509: X.com (Twitter) Liked Posts Checker
- **Description**: Monitors liked/bookmarked posts on X.com
- **Acceptance Criteria**:
  - CronJob runs every 2 hours
  - Uses X.com API v2 with OAuth
  - Fetches liked tweets and bookmarks
  - Emits URLs to `task.url.ingest` topic
  - Tracks last checked tweet ID to avoid duplicates
  - Handles rate limiting gracefully
- **Technical Implementation**:
  ```python
  @dataclass
  class TwitterLikedChecker:
      user_id: str
      oauth_token: str
      check_likes: bool = True
      check_bookmarks: bool = True
      last_checked_id: Optional[str]
  
  @dataclass
  class TwitterURLTask:
      url: str  # https://x.com/user/status/123456
      tweet_id: str
      author: str
      liked_at: datetime
      content_preview: str
      media_urls: List[str]
      scrape_type: str = "twitter_post"
  ```
- **Schedule**: `0 */2 * * *` (every 2 hours)
- **Estimate**: 5 story points

#### TASK-510: X.com Post Downloader Consumer
- **Description**: Processes Twitter/X URLs from task.url.ingest
- **Acceptance Criteria**:
  - Kafka consumer for `task.url.ingest` filtering Twitter URLs
  - Downloads full tweet content and media
  - Handles threads by following conversation
  - Archives images/videos to object storage
  - Produces to `task.url.processed.twitter_archived`
  - Respects rate limits and implements retry logic
- **Technical Implementation**:
  ```python
  class TwitterPostDownloader:
      async def process_twitter_url(self, task: TwitterURLTask):
          # Download tweet content
          tweet = await self.fetch_tweet(task.tweet_id)
          
          # Download media
          media_refs = await self.download_media(tweet.media_urls)
          
          # Get full thread if applicable
          thread = await self.fetch_thread(tweet) if tweet.is_thread else None
          
          # Produce archived result
          return TwitterArchive(
              tweet_id=task.tweet_id,
              full_text=tweet.text,
              author_data=tweet.author,
              media_references=media_refs,
              thread_content=thread,
              archived_at=datetime.utcnow()
          )
  ```
- **Estimate**: 8 story points

#### TASK-511: Hacker News Saved Posts Checker
- **Description**: Monitors saved/upvoted posts on Hacker News
- **Acceptance Criteria**:
  - CronJob runs every 4 hours  
  - Uses HN API with user authentication
  - Fetches saved stories and comments
  - Emits URLs to `task.url.ingest` topic
  - Tracks processed item IDs
  - Handles both stories and comments
- **Technical Implementation**:
  ```python
  @dataclass
  class HackerNewsSavedChecker:
      username: str
      auth_cookie: str
      check_saved: bool = True
      check_upvoted: bool = True
      last_checked_ids: Set[int]
  
  @dataclass
  class HackerNewsURLTask:
      hn_item_id: int
      url: Optional[str]  # Some posts are text-only
      title: str
      author: str
      score: int
      comment_count: int
      item_type: str  # story, comment
      scrape_type: str = "hackernews_item"
  ```
- **Schedule**: `0 */4 * * *` (every 4 hours)
- **Estimate**: 5 story points

#### TASK-512: Generic URL Content Processor
- **Description**: Processes generic web URLs from task.url.ingest
- **Acceptance Criteria**:
  - Kafka consumer for non-specific URLs
  - Extracts article content using readability algorithms
  - Downloads and processes PDFs
  - Handles various content types (HTML, PDF, images)
  - Produces to appropriate processed topics
  - Implements content type detection
- **Technical Implementation**:
  ```python
  class GenericURLProcessor:
      async def process_url(self, url: str) -> ProcessedContent:
          content_type = await self.detect_content_type(url)
          
          if content_type == "pdf":
              return await self.process_pdf(url)
          elif content_type == "html":
              return await self.extract_article(url)
          elif content_type.startswith("image/"):
              return await self.process_image(url)
          else:
              return await self.download_raw(url)
  ```
- **Estimate**: 8 story points

### Epic 4: Remote Control Infrastructure (Week 4)

#### TASK-513: Bidirectional Kafka Topics
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

## 📋 CronJob Schedule Summary

| Service | Schedule | Frequency | Topic |
|---------|----------|-----------|--------|
| IMAP Email Sync | `*/15 * * * *` | Every 15 minutes | `external.email.events.raw` |
| Google Calendar | `*/30 * * * *` | Every 30 minutes | `external.calendar.events.raw` |
| X.com Liked Posts | `0 */2 * * *` | Every 2 hours | `task.url.ingest` |
| Hacker News Saved | `0 */4 * * *` | Every 4 hours | `task.url.ingest` |

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
