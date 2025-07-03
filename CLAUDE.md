# Loom v2 - Claude Code Configuration

## Project Overview

**Loom v2** is a personal informatics data pipeline built with a microservices architecture, designed to ingest, process, and store data from various devices (audio, sensors, health metrics). The system uses an event-driven architecture with Kafka for message streaming and TimescaleDB for data persistence.

### Architecture Summary
- **Ingestion API**: FastAPI-based service for real-time data ingestion via REST and WebSocket
- **Event Streaming**: Kafka for reliable message queuing and processing
- **Storage**: TimescaleDB for time-series data persistence
- **Deployment**: Kubernetes-native with Helm charts and k3d for local development
- **Observability**: Structured logging, Prometheus metrics, health probes

## Core Technologies

- **Python 3.11+** - Primary language
- **FastAPI** - High-performance async web framework
- **Kafka** - Event streaming platform
- **TimescaleDB** - Time-series database built on PostgreSQL 15
- **Kubernetes** - Container orchestration
- **Docker** - Containerization
- **Tilt** - Local development environment with hot-reload
- **uv** - Fast Python package management

## Project Structure

```
/Users/mpedersen/code/loomv2/
├── Makefile                 # Main development commands
├── Tiltfile                 # Local K8s dev environment
├── deploy/                  # Kubernetes manifests and Helm charts
│   ├── dev/                 # Development K8s configs
│   └── helm/                # Production Helm charts
├── docs/                    # Architecture documentation
│   ├── storage.md           # Database design and patterns
│   ├── data-processing-flows.md  # Comprehensive data pipeline documentation
│   └── flows/               # Detailed flow specifications (11 pipelines)
├── scripts/                 # Utility scripts (Kafka topics, deployment)
├── services/                # Microservices
│   └── ingestion-api/       # Core data ingestion service
│       ├── app/             # FastAPI application code
│       ├── tests/           # Comprehensive test suite (71 tests)
│       ├── Dockerfile       # Multi-stage container build
│       ├── Makefile         # Service-specific commands
│       └── pyproject.toml   # Python dependencies and config
└── shared/                  # Cross-service schemas and validation
    └── schemas/             # JSON Schema definitions (v1, v2...)
        ├── device/          # Device data schemas
        └── media/           # Media processing schemas
```

## Development Commands

### Essential Commands
```bash
# Setup development environment
make setup                   # Install dependencies, pre-commit hooks

# Start/stop local development
make dev-up                  # Start Tilt development environment
make dev-down                # Stop development environment

# Testing
make test                    # Run all tests
make test-coverage           # Run tests with coverage report
make test-integration        # Run integration tests

# Code quality
make lint                    # Run pre-commit hooks (ruff, black, mypy)
make format                  # Format code with black and ruff
make security-scan           # Run security scans (bandit, safety)

# Database operations
make db-connect              # Connect to local TimescaleDB
export DATABASE_URL="postgresql://loom:loom@localhost:5432/loom"

# Kafka operations
make topics-create           # Create required Kafka topics
make topics-list             # List existing topics

# Kafka monitoring (Web UI)
# Open http://localhost:8081 for web-based monitoring

# Monitoring
make logs                    # View service logs
make status                  # Show K8s pod/service status

# Docker
make docker                  # Build all Docker images
make docker-push             # Push to registry

# Helm
make helm-lint               # Lint all Helm charts
make helm-template           # Template charts for validation
```

### Service-Specific Commands (ingestion-api)
```bash
cd services/ingestion-api

# Development
make dev                     # Run development server with hot-reload
make install                 # Install dependencies with uv
make requirements            # Generate requirements.txt

# Testing
make test                    # Run unit tests
make test-watch              # Run tests in watch mode
make test-coverage           # Generate coverage report
make test-integration        # Run integration tests

# Code quality
make lint-check              # Check code quality without fixes
make type-check              # Run mypy type checking
make format                  # Format code
make security                # Security scanning

# CI/CD
make ci                      # Full CI pipeline (lint, type, test, security)

# Docker
make docker                  # Build Docker image
make docker-run              # Run container locally
```

## API Endpoints

### Ingestion API (localhost:8000)

#### Health & Monitoring
- `GET /healthz` - Liveness probe
- `GET /readyz` - Readiness probe
- `GET /metrics` - Prometheus metrics

#### Device Management
- `GET /devices` - List all registered devices
- `GET /devices/activity` - Get device activity summary
- `GET /devices/{device_id}` - Get specific device details
- `POST /devices` - Register a new device
- `PATCH /devices/{device_id}` - Update device information
- `DELETE /devices/{device_id}` - Soft delete a device

#### Audio Ingestion
- `POST /audio/upload` - Upload audio chunks
- `WebSocket /audio/stream/{device_id}` - Real-time audio streaming

#### Sensor Data
- `POST /sensor/gps` - GPS coordinates with accuracy
- `POST /sensor/accelerometer` - 3-axis motion data
- `POST /sensor/heartrate` - Heart rate measurements
- `POST /sensor/power` - Device power state
- `POST /sensor/generic` - Generic sensor readings
- `POST /sensor/batch` - Batch upload multiple sensors

#### OS Event Data
- `POST /os-events/app-lifecycle` - Application lifecycle events
  - Event types: `launch`, `foreground`, `background`, `terminate`, `crash`
  - Includes app identifier, name, event duration
  - Tracks both Loom app and other apps on device
- `POST /os-events/system` - System events  
  - Event types: `screen_on`, `screen_off`, `device_lock`, `device_unlock`, `power_connected`, `power_disconnected`
  - Categories: `screen`, `lock`, `power`, `system`
  - Includes metadata about current device state
- `POST /os-events/notifications` - Notification events (future use)

#### System Monitoring
- `POST /system/apps/android` - Android app monitoring data
  - Lists currently running applications
  - Includes PID, package name, version info
  - Tracks foreground/background state
- `POST /system/apps/android/usage` - Android app usage statistics
  - Pre-aggregated usage data from Android UsageStats API
  - Includes total foreground time, launch count
  - Requires `PACKAGE_USAGE_STATS` permission
- `POST /system/metadata` - Device metadata and capabilities
  - Flexible endpoint for device-specific information
  - Used for app info, hardware specs, capabilities

## Data Schemas

### Schema Validation
- **Format**: JSON Schema Draft 2020-12
- **Organization**: Hierarchical by data type and version
- **Versioning**: Semantic versioning (v1.json, v2.json)
- **Runtime**: Validation via `jsonschema` library with caching

### Current Schemas
```
shared/schemas/
├── device/
│   ├── audio/raw/v1.json           # Raw audio chunks (base64)
│   ├── sensor/gps/v1.json          # GPS coordinates with accuracy
│   ├── sensor/accelerometer/v1.json # 3-axis motion data
│   └── health/heartrate/v1.json    # Heart rate with confidence
└── media/
    └── audio/vad_filtered/v1.json  # Voice activity detected audio
```

### Kafka Topics

#### Topic Naming Convention
Pattern: `<category>.<source>.<datatype>.<stage>` (all lowercase, dot-separated)

#### Raw Data Ingestion Topics
**Device Audio/Video/Image:**
- `device.audio.raw` - Raw microphone audio chunks (7 days retention)
- `device.video.screen.raw` - Keyframes from screen recordings
- `device.image.camera.raw` - Photos from cameras and screenshots

**Device Sensors:**
- `device.sensor.gps.raw` - GPS coordinates with accuracy (30 days retention)
- `device.sensor.accelerometer.raw` - 3-axis motion data (30 days retention)
- `device.sensor.barometer.raw` - Atmospheric pressure data
- `device.sensor.temperature.raw` - Device temperature readings

**Device Health:**
- `device.health.heartrate.raw` - Heart rate measurements (60 days retention)
- `device.health.steps.raw` - Step count data

**Device State:**
- `device.state.power.raw` - Battery level and charging status (30 days retention)

**Device System:**
- `device.system.apps.macos.raw` - macOS app monitoring data (30 days retention)
- `device.system.apps.android.raw` - Android app monitoring data (30 days retention)
- `device.metadata.raw` - Arbitrary device metadata (90 days retention)

**Network:**
- `device.network.wifi.raw` - Wi-Fi connection state
- `device.network.bluetooth.raw` - Nearby Bluetooth devices

**OS Events:**
- `os.events.app_lifecycle.raw` - Android app lifecycle events (30 days retention)
- `os.events.system.raw` - System events (screen on/off, lock/unlock, power) (30 days retention)
- `os.events.notifications.raw` - System notifications (30 days retention)

**Digital Data:**
- `digital.clipboard.raw` - Clipboard content
- `digital.web_analytics.raw` - Website analytics data

**External Sources:**
- `external.twitter.liked.raw` - Scraped liked Twitter/X posts
- `external.calendar.events.raw` - Calendar events (CalDAV)
- `external.email.events.raw` - Email events (all IMAP accounts)

**Task Topics:**
- `task.url.ingest` - URLs to be processed (Twitter links, PDFs, web pages)

#### Processed Data Topics
**Media Processing:**
- `media.audio.vad_filtered` - Audio chunks identified as speech
- `media.audio.environment_classified` - Audio environment classification (indoor/outdoor/vehicle)
- `media.text.transcribed.words` - Word-by-word transcripts from speech
- `media.text.ocr_extracted` - Raw OCR text from images
- `media.text.ocr_cleaned` - Cleaned and structured OCR text
- `media.image.camera.preprocessed` - Normalized camera images
- `media.image.screenshot.preprocessed` - Preprocessed screenshots for OCR
- `media.image.objects_detected` - Detected objects with bounding boxes
- `media.image.objects_hashed` - Perceptual hashes for object tracking
- `media.image.faces_detected` - Detected faces with landmarks
- `media.image.pose_detected` - Body and hand pose keypoints
- `media.image.gaze_detected` - Eye gaze vectors
- `media.image.analysis.moondream_results` - Image analysis (captions, gaze, objects)
- `media.image.analysis.minicpm_results` - Vision-language analysis results
- `media.video.analysis.yolo_results` - Object detection/tracking from video

**Analysis Results:**
- `analysis.3d_reconstruction.dustr_results` - 3D environment reconstruction
- `analysis.inferred_context.qwen_results` - High-level context inferences
- `analysis.inferred_context.mistral_results` - Mistral reasoning outputs
- `analysis.audio.emotion_results` - Speech emotion recognition
- `analysis.image.emotion_results` - Face emotion recognition

**Task Results:**
- `task.url.processed.twitter_archived` - Archived X.com/Twitter content
- `task.url.processed.hackernews_archived` - Archived HackerNews content
- `task.url.processed.pdf_extracted` - Extracted PDF content/summaries

**Location Processing:**
- `location.georegion.detected` - Detected presence in saved georegions (home/work/custom)
- `location.address.geocoded` - Geocoded addresses from GPS
- `location.business.identified` - Identified businesses at locations

**Motion & Activity:**
- `device.sensor.accelerometer.windowed` - Windowed accelerometer features
- `motion.events.significant` - Significant motion events detected
- `motion.classification.activity` - Classified activities (walking/driving/etc)

**Device State Processing:**
- `device.state.power.enriched` - Enriched power state with patterns
- `device.state.power.patterns` - Detected charging patterns
- `os.events.app_lifecycle.enriched` - Enriched app lifecycle events

**External Data Processing:**
- `external.email.raw` - Raw fetched emails
- `external.email.parsed` - Parsed email structure
- `external.email.embedded` - Email text embeddings
- `external.calendar.raw` - Raw calendar events
- `external.calendar.enriched` - Enriched calendar data
- `external.calendar.embedded` - Calendar event embeddings
- `external.hackernews.liked` - Liked HN items
- `external.hackernews.content_fetched` - Fetched article content
- `external.hackernews.embedded` - HN content embeddings

**Spatial Data:**
- `spatial.slam.mapping` - SLAM-generated 3D maps

#### Kafka Configuration
**Message Format:**
- **Key:** `device_id` (when events originate from a single device, otherwise `null`)
- **Value:** JSON with `schema_version` field for versioning
- **Compression:** `lz4` for high-volume topics, `producer` default

**Default Settings:**
- **Partitions:** Configurable (default via `LOOM_KAFKA_DEFAULT_PARTITIONS`)
- **Replication Factor:** Configurable (default via `LOOM_KAFKA_DEFAULT_REPLICATION_FACTOR`)
- **Retention:** Varies by topic (7-90 days based on data type)

#### Remote Control Topics (Bidirectional Communication)
**Device Command & Control:**
- `device.command.keystroke.send` - Send keystrokes to remote devices
- `device.command.mouse.send` - Send mouse movements/clicks to remote devices
- `device.command.clipboard.send` - Send clipboard content to remote devices
- `device.command.file.transfer` - Transfer files to/from remote devices
- `device.command.screen.capture` - Request screen captures from remote devices
- `device.command.audio.send` - Send audio to remote devices
- `device.command.shell.execute` - Execute shell commands on remote devices
- `device.command.app.launch` - Launch applications on remote devices
- `device.command.app.close` - Close applications on remote devices

**Device Response Topics:**
- `device.response.command.status` - Command execution status/results
- `device.response.file.transfer` - File transfer progress/completion
- `device.response.screen.capture` - Screen capture results
- `device.response.shell.output` - Shell command output
- `device.response.error` - Error responses from remote devices

**Cross-Device Communication:**
- `device.sync.clipboard.broadcast` - Broadcast clipboard across devices
- `device.sync.files.broadcast` - Sync files across devices
- `device.sync.state.broadcast` - Sync application state across devices

## Executive Summary: Evolved Architecture for Loom v2

The initial design of Loom v2 is strong, event-driven, and scalable. This evolved architecture refines the data persistence and AI processing layers to create a more resilient, powerful, and specialized system. The core architectural shift is to re-adopt a **Time-Series Database (TSDB)** for all high-volume sensor and event data, and to implement a **"best-of-breed" microservice strategy** where each AI model is a containerized, independently scalable Kafka consumer/producer.

### Core Architectural Insights & Strategic Decisions

| Insight | Description |
|---------|-------------|
| **1. Re-adopt a Time-Series Database (TSDB)** | **Highest-priority recommendation.** Migrating back to a TSDB like TimescaleDB (as a PostgreSQL extension) is critical for handling the high volume and time-centric nature of your data. It provides massive benefits in storage compression (up to 95%), query speed for time-range analysis, and automated data lifecycle management (e.g., dropping data older than 30 days) that vanilla PostgreSQL cannot match. |
| **2. Enforce Structured LLM Outputs with outlines** | The [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) library is a must-have integration. It will be used within your AI services to force the output of models like MiniCPM and Mistral into your pre-defined JSON Schemas (`shared/schemas/`). This turns probabilistic LLMs into reliable, deterministic data processors, eliminating downstream parsing errors and making the entire pipeline more robust. |
| **3. Adopt a "Best-of-Breed" Microservice Pattern** | While a single "super-model" like MiniCPM could handle multiple tasks (vision, ASR), the more scalable and resilient approach is to use specialized models for each task. Each model will be deployed in its own Docker container, acting as a dedicated Kafka consumer/producer. This allows for independent scaling (e.g., scaling STT processing without affecting vision processing), isolated failure domains, and using the highest-performing model for each job. |
| **4. External Data Ingestion via Scheduled Scrapers** | For ingesting data from external URLs (X, GitHub), the recommended pattern is: <br>1. A Kubernetes CronJob runs a scraper on a schedule. <br>2. The scraper fetches URLs and produces simple messages to the `task.url.ingest` topic. <br>3. A dedicated consumer service processes each URL from the topic, performing the heavy lifting of downloading and parsing content. |
| **5. Standardize on CPU/GPU-Flexible Inference** | All AI models will be containerized for deployment via Kubernetes. Models will be chosen for their ability to run on GPU for high performance, but many are small enough to have a viable CPU fallback for lower-cost or development environments. This will be managed by Kubernetes node selectors and taints. |

### AI Model Integration Plan & Kafka Topic Mapping

This table details the core data processing pipeline, showing how raw data flows through a series of specialized AI models:

| Model / Tool | Primary Task | Inference Strategy | Input Kafka Topic(s) | Output Kafka Topic |
|-------------|-------------|-------------------|---------------------|-------------------|
| **Silero VAD** | Voice Activity Detection | `torch.hub` in a Python service. CPU-optimized. | `device.audio.raw` | `media.audio.vad_filtered` |
| **Kyutai Mimi STT** | Speech-to-Text (ASR) | Kyutai Moshi framework with Mimi model. GPU Recommended, CPU viable. | `device.audio.raw` | `media.text.transcribed.words` |
| **Laion BUD-E-Whisper** | Speech Emotion Recognition | Hugging Face Audio Classification Pipeline. GPU Recommended. | `media.audio.vad_filtered` | `analysis.audio.emotion_results` |
| **MiniCPM-Llama3-V 2.5** | Vision-Language Analysis & OCR | Hugging Face transformers + outlines. GPU-preferred, CPU-viable. | `device.image.camera.raw`<br>`device.video.screen.raw` | `media.image.analysis.minicpm_results` |
| **Laion Empathic-Insight-Face** | Face Emotion Recognition | Hugging Face Image Classification Pipeline. GPU Strongly Recommended. | `media.image.analysis.minicpm_results` (Requires face detection first) | `analysis.image.emotion_results` |
| **Mistral Small 3.2** | High-Level Reasoning & Context | Ollama Server + outlines. GPU Strongly Recommended. | `media.text.transcribed.words`<br>`task.url.processed.*`<br>...and other text-based topics | `analysis.inferred_context.mistral_results` |

### Future & Auxiliary Models

| Model | Primary Task | Inference Strategy | Potential Use Case |
|-------|-------------|-------------------|-------------------|
| **geneing/Kokoro** | Text-to-Speech (TTS) | Hugging Face transformers TTS Pipeline. | Provide a "voice" for your system. A future service could consume from `analysis.inferred_context.mistral_results` (e.g., a daily summary) and use Kokoro to generate a spoken audio file, making the system interactive. |
| **laion/BUD-E-Whisper** | Speech Emotion Recognition | Hugging Face Audio Classification Pipeline. | *Note: Currently disabled as the model appears to be missing from HuggingFace. Would be interesting to add in the future for detecting emotions in speech audio. The service container has been removed but the code remains in `services/bud-e-emotion/`.* |

### Model Links & Resources

**Core Models:**
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice Activity Detection
- [Kyutai Mimi STT](https://huggingface.co/kyutai/stt-1b-en_fr) - Speech-to-Text (Mimi model)
- [Laion BUD-E-Whisper](https://huggingface.co/laion/BUD-E_Whisper) - Speech Emotion Recognition
- [MiniCPM-Llama3-V 2.5](https://huggingface.co/openbmb/MiniCPM-Llama3-V-2_5) - Vision-Language Model
- [Laion Empathic-Insight-Face](https://huggingface.co/laion/Empathic-Insight-Face) - Face Emotion Recognition
- [Mistral Small 3.2](https://huggingface.co/mistralai/Mistral-Small-3.2) - High-Level Reasoning
- [geneing/Kokoro](https://huggingface.co/geneing/Kokoro) - Text-to-Speech

**Supporting Libraries:**
- [dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) - Structured LLM Output Generation
- [Ollama](https://ollama.ai/) - Local LLM Inference Server
- [TimescaleDB](https://www.timescale.com/) - Time-Series Database Extension for PostgreSQL

## 🚀 Sprint Planning & Development Status

### Current Sprint: Sprint 6 - AI Model Integration
**Duration**: August 4 - August 31, 2024
**Focus**: Integrate AI models for audio, vision, and context analysis

#### Sprint 5 Accomplishments (Completed)
1. **Android OS Event Tracking**: 
   - Screen on/off detection with BroadcastReceiver
   - Device lock/unlock state monitoring
   - Power connected/disconnected events
   - Real-time event streaming via EventChannel

2. **App Lifecycle Monitoring**:
   - Foreground/background app tracking
   - App launch and termination detection
   - Duration calculation for app sessions
   - Integration with Android UsageStats API

3. **Intelligent Screenshot Capture**:
   - Automatic skip when screen is off
   - Skip when device is locked
   - 5-second delay after screen on (avoid lock screen)
   - Privacy-aware capture logic

4. **API & Database Integration**:
   - New OS event endpoints (`/os-events/*`)
   - System monitoring endpoints (`/system/apps/*`)
   - TimescaleDB tables for OS events
   - Kafka topic integration

5. **Mobile Client Enhancements**:
   - Three new data sources for OS events
   - Native Android integration via Kotlin
   - Comprehensive permission handling
   - Batch upload optimization

#### Sprint History
- **Sprint 0**: ✅ Infrastructure setup, pre-commit hooks, k3d environment
- **Sprint 1**: ✅ Test suite (71 tests), CI/CD pipeline
- **Sprint 2**: ✅ Core infrastructure, schema validation
- **Sprint 3**: ✅ Storage abstraction layer, database migrations
- **Sprint 4**: ✅ Kafka topic auto-creation, app monitoring endpoints
- **Sprint 5**: ✅ OS event tracking, screenshot intelligence, app lifecycle monitoring

### Development Roadmap

#### Completed Features
- Event-driven architecture with Kafka streaming
- FastAPI ingestion service with WebSocket support
- Kubernetes-native deployment with Helm charts
- Comprehensive testing framework (71+ tests)
- Automatic Kafka topic management
- Device monitoring (audio, sensors, health, apps)
- Android OS event tracking (screen state, app lifecycle)
- Intelligent screenshot capture with privacy awareness
- Native Android integration for system monitoring
- Batch data upload with configurable profiles

#### In Development (Sprint 6)
- TimescaleDB migration for time-series optimization
- AI model microservices (VAD, Vision, LLM)
- Structured LLM output processing with outlines
- External data ingestion via CronJobs
- Cross-device remote control system

#### Future Sprints
- **Sprint 6**: Advanced AI model integration (emotion recognition, 3D reconstruction)
- **Sprint 7**: Real-time analytics dashboard and visualization
- **Sprint 8**: Mobile SDK development and device client optimization
- **Sprint 9**: Production hardening and performance optimization

## Configuration

### Environment Variables (LOOM_ prefix)
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

### Local Development Services
- **Ingestion API**: http://localhost:8000
- **Kafka UI**: http://localhost:8081 (Web-based Kafka monitoring)
- **Kafka**: localhost:9092 (+ admin on 9093)
- **PostgreSQL**: localhost:5432 (loom/loom/loom)
- **Tilt UI**: http://localhost:10350

## Testing

### Test Structure
```
services/ingestion-api/tests/
├── unit/                    # Unit tests for individual components
│   ├── test_lifespan.py     # Startup/shutdown testing
│   ├── test_health.py       # Health endpoint testing
│   ├── test_metrics.py      # Prometheus metrics testing
│   ├── test_cors.py         # CORS configuration testing
│   ├── test_exceptions.py   # Error handling testing
│   └── test_websocket.py    # WebSocket functionality testing
├── integration/             # End-to-end integration tests
└── conftest.py              # Shared test fixtures and configuration
```

### Running Tests
```bash
# All tests (71 total)
make test

# With coverage
make test-coverage

# Watch mode (development)
cd services/ingestion-api && make test-watch

# Integration tests
make test-integration

# Specific test file
pytest services/ingestion-api/tests/unit/test_health.py -v
```

### Test Categories
- **Lifespan Management** - Application startup/shutdown sequences
- **Health Endpoints** - Kubernetes liveness/readiness probes
- **Metrics Collection** - Prometheus integration and custom metrics
- **CORS Configuration** - Cross-origin request handling
- **Exception Handling** - Error response formatting and logging
- **WebSocket Connections** - Real-time streaming functionality

## Deployment

### Local Development (k3d)
```bash
# Start full environment
make dev-up

# Check status
make status

# View logs
make logs

# Connect to services
make db-connect                           # TimescaleDB CLI
kubectl exec -n loom-dev -it deployment/kafka -- kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic device.audio.raw
```

### Production (Helm)
```bash
# Lint charts
make helm-lint

# Template for validation
make helm-template

# Deploy ingestion-api
helm install loom-ingestion deploy/helm/ingestion-api/

# Deploy Kafka infrastructure
helm install loom-kafka deploy/helm/kafka-infra/
```

## Observability

### Logging
- **Format**: Structured JSON via `structlog`
- **Fields**: timestamp, level, message, correlation_id, service
- **Correlation**: Request tracing across service boundaries

### Metrics (Prometheus)
- `http_requests_total{method, endpoint, status}` - Request counters
- `http_request_duration_seconds{method, endpoint}` - Request latency
- `websocket_connections_total` - Active WebSocket connections
- `kafka_messages_sent_total{topic}` - Message publishing metrics

### Health Checks
- `GET /healthz` - Always returns 200 (liveness)
- `GET /readyz` - Returns 200 when dependencies are healthy (readiness)

## Code Quality & Security

### Pre-commit Hooks
- **ruff** - Fast linting and import sorting
- **black** - Code formatting
- **mypy** - Static type checking
- **bandit** - Security vulnerability scanning
- **safety** - Dependency vulnerability checking

### Security Practices
- Dependency scanning with `safety check`
- Code security analysis with `bandit`
- Container security hardening
- No secrets in code or logs
- Least-privilege Kubernetes pod security

## Development Workflow

### Feature Development
1. Create feature branch from `main`
2. Use `make dev-up` for local development
3. Write tests first (TDD approach)
4. Implement feature with hot-reload via Tilt
5. Run `make ci` for full quality checks
6. Create PR against `main`

### Schema Changes
1. Create new schema version (e.g., v2.json)
2. Update validation mapping
3. Ensure backward compatibility within major version
4. Test with sample data
5. Deploy and migrate gradually

### Service Development
1. Follow existing patterns in `ingestion-api`
2. Use FastAPI for HTTP services
3. Implement health endpoints (`/healthz`, `/readyz`)
4. Add Prometheus metrics
5. Write comprehensive tests
6. Document API in OpenAPI/Swagger

## Troubleshooting

### Common Issues
```bash
# Tilt won't start
kubectl config current-context        # Verify k8s context
k3d cluster list                      # Check k3d cluster status

# Service crashes
make logs                             # Check service logs
kubectl describe pod -n loom-dev      # Pod details

# Database connection issues
make db-connect                       # Direct connection test
kubectl get secrets -n loom-dev      # Check credentials

# Kafka issues
make topics-list                      # Verify topics exist
kubectl exec -n loom-dev -it deployment/kafka -- kafka-log-dirs.sh --bootstrap-server localhost:9092 --describe
```

### Debug Mode
```bash
# Enable debug logging
export LOOM_LOG_LEVEL=DEBUG

# Run service directly (outside container)
cd services/ingestion-api
uv run uvicorn app.main:app --reload --log-level debug
```

## Contributing

### Code Style
- **Line Length**: 88 characters (Black default)
- **Type Hints**: Required for all functions/methods
- **Docstrings**: Google style for public APIs
- **Imports**: Sorted with ruff (isort rules)

### Git Workflow
- **Main Branch**: `main` (protected)
- **Feature Branches**: `feature/description` or `fix/description`
- **Commit Messages**: Conventional commits format
- **PR Requirements**: All checks must pass, 1 review required

### Adding New Services
1. Create directory under `services/`
2. Follow `ingestion-api` structure and patterns
3. Add Dockerfile with security hardening
4. Create Helm chart in `deploy/helm/`
5. Add to Tiltfile for local development
6. Update this documentation

## Mobile Client (Flutter)

### Overview
The mobile client is a Flutter application that collects data from Android/iOS devices and sends it to the ingestion API. It supports background data collection with configurable battery profiles.

### Data Sources
- **Audio**: Microphone recording with chunking
- **GPS**: Location tracking with accuracy
- **Accelerometer**: 3-axis motion data  
- **Battery**: Power state and charging status
- **Network**: WiFi and Bluetooth state
- **Screenshot**: Automatic and manual captures
- **Camera**: Photo capture
- **Screen State** (Android): Screen on/off and lock detection
- **App Lifecycle** (Android): App foreground/background events
- **App Monitoring** (Android): Running apps and usage statistics

### Android-Specific Features

#### OS Event Tracking
The mobile client monitors Android system events:
- **Screen Events**: Screen on/off detection via `ACTION_SCREEN_ON/OFF` broadcasts
- **Lock Events**: Device lock/unlock detection via `KeyguardManager`
- **Power Events**: Charger connected/disconnected via `ACTION_POWER_CONNECTED/DISCONNECTED`

#### App Lifecycle Monitoring
Tracks application lifecycle events:
- **App Launch**: When an app is started
- **App Foreground/Background**: When apps move between states
- **App Termination**: When apps are closed
- Requires `PACKAGE_USAGE_STATS` permission (user must grant in Settings)

#### Screenshot Behavior
- Screenshots are automatically skipped when:
  - Screen is off
  - Device is locked
  - Within 5 seconds of screen turning on (to avoid lock screen capture)

### Battery Profiles
- **Performance**: Immediate upload, high frequency collection
- **Balanced**: Moderate intervals and batch sizes
- **Power Saver**: Conservative settings for battery life
- **Custom**: User-configurable intervals and batch sizes

### Permissions
The app requires various permissions depending on enabled data sources:
- Location (GPS)
- Microphone (Audio)
- Storage/Photos (Screenshots)
- Usage Stats (App Monitoring - Android only)

### Configuration
Data collection is configured through battery profiles that control:
- **Collection Interval**: How often to collect data (ms)
- **Upload Batch Size**: Number of data points before upload
- **Upload Interval**: Maximum time between uploads (ms)

### Implementation Details

#### Native Android Integration
The OS event tracking uses native Android components:

1. **BroadcastReceiver** for system events:
   - `ScreenStateReceiver.kt` - Listens for screen and power events
   - Registered dynamically to receive `ACTION_SCREEN_ON/OFF`, `ACTION_USER_PRESENT`
   - Provides real-time screen state to Flutter via EventChannel

2. **UsageStatsManager** for app monitoring:
   - `AppLifecycleMonitor.kt` - Tracks app usage and lifecycle
   - Requires `PACKAGE_USAGE_STATS` permission (special permission)
   - Provides app launch counts, foreground time, and event history

3. **Method Channels** for Flutter communication:
   - `red.steele.loom/screen_state` - Get current screen state
   - `red.steele.loom/app_lifecycle` - Start/stop app monitoring
   - `red.steele.loom/app_monitoring` - Get running apps and usage stats

#### Data Flow
1. Native Android components detect OS events
2. Events are sent to Flutter via EventChannel/MethodChannel
3. Flutter data sources process and batch events
4. Data collection service uploads batches to API endpoints
5. API forwards to Kafka topics for processing
6. TimescaleDB stores events with automatic retention

#### Database Schema
OS events are stored in TimescaleDB hypertables:
- `os_events_system_raw` - Screen, lock, and power events
- `os_events_app_lifecycle_raw` - App lifecycle events
- `device_system_apps_android_raw` - Running app snapshots

---

**Quick Start**: `make setup && make dev-up` then visit http://localhost:8000
