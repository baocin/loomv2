# Sprint 4: Kafka Topic Auto-Creation & App Monitoring

> **Duration**: 2 weeks
> **Focus**: Infrastructure automation and expanded device monitoring capabilities

## 🎯 Sprint Goals

1. **Automate Kafka topic creation** on service startup to eliminate manual setup
2. **Add comprehensive app monitoring** for macOS and Android platforms
3. **Support arbitrary device metadata** for flexible device management
4. **Enhance developer experience** with streamlined setup and expanded monitoring

## 📋 User Stories

### Epic 1: Infrastructure Automation
**As a developer**, I want Kafka topics to be created automatically when the service starts, so that I don't need to manually set up topics before using the API.

### Epic 2: Application Monitoring
**As a data analyst**, I want to track running applications on user devices (macOS/Android), so that I can analyze app usage patterns and digital behavior.

### Epic 3: Device Management
**As a system integrator**, I want to store arbitrary metadata about devices, so that I can track device capabilities, configurations, and custom attributes.

## 🎫 Sprint Backlog

### High Priority

#### TASK-401: Automatic Kafka Topic Creation
- **Description**: Implement automatic topic creation during service startup
- **Acceptance Criteria**:
  - Service checks for required topics on startup
  - Creates missing topics with appropriate configuration
  - Handles topic creation failures gracefully
  - Logs topic creation status
- **Technical Notes**:
  - Use aiokafka AdminClient for topic management
  - Configure topics with sensible defaults (partitions, replication)
  - Add environment variables for topic configuration
- **Estimate**: 8 story points

#### TASK-402: macOS App Monitoring Endpoint
- **Description**: Add REST endpoint for macOS running applications data
- **Acceptance Criteria**:
  - POST `/system/apps/macos` endpoint
  - Validates app monitoring payload structure
  - Publishes to Kafka topic `device.system.apps.macos.raw`
  - Handles batch app data efficiently
- **Schema Requirements**:
  ```json
  {
    "device_id": "string",
    "timestamp": "ISO8601",
    "running_applications": [
      {
        "pid": "integer",
        "name": "string",
        "bundle_id": "string",
        "active": "boolean",
        "hidden": "boolean",
        "launch_date": "float|null"
      }
    ]
  }
  ```
- **Estimate**: 5 story points

#### TASK-403: Android App Monitoring Endpoint
- **Description**: Add REST endpoint for Android app events
- **Acceptance Criteria**:
  - POST `/system/apps/android` endpoint
  - Supports similar structure to macOS with Android-specific fields
  - Publishes to Kafka topic `device.system.apps.android.raw`
  - Handles Android package information
- **Estimate**: 3 story points

### Medium Priority

#### TASK-404: Device Metadata Endpoint
- **Description**: Add endpoint for arbitrary device metadata storage
- **Acceptance Criteria**:
  - POST `/device/metadata` endpoint
  - Accepts flexible JSON payloads
  - Validates required fields (device_id, metadata_type)
  - Publishes to Kafka topic `device.metadata.raw`
- **Schema Requirements**:
  ```json
  {
    "device_id": "string",
    "metadata_type": "string",
    "metadata": "object",
    "timestamp": "ISO8601"
  }
  ```
- **Estimate**: 4 story points

#### TASK-405: JSON Schema Definitions
- **Description**: Create JSON schemas for new data types
- **Acceptance Criteria**:
  - Schema for macOS app monitoring
  - Schema for Android app monitoring
  - Schema for device metadata
  - All schemas follow JSON Schema Draft 2020-12
- **Estimate**: 3 story points

### Low Priority

#### TASK-406: Update Integration Guide
- **Description**: Update integration guide with new endpoints
- **Acceptance Criteria**:
  - Document new endpoints with examples
  - Add cURL examples for new endpoints
  - Update SDK examples
  - Add troubleshooting for new features
- **Estimate**: 2 story points

## 🏗️ Technical Implementation

### Kafka Topic Auto-Creation Architecture

```python
# Service startup sequence
1. Initialize Kafka AdminClient
2. Check existing topics
3. Create missing topics with configuration
4. Validate topic creation success
5. Start main application
```

**Required Topics**:
- `device.audio.raw`
- `device.sensor.gps.raw`
- `device.sensor.accelerometer.raw`
- `device.health.heartrate.raw`
- `device.state.power.raw`
- `device.system.apps.macos.raw` (new)
- `device.system.apps.android.raw` (new)
- `device.metadata.raw` (new)

### App Monitoring Data Flow

```
macOS/Android Device → API Endpoint → Validation → Kafka Topic → Processing Pipeline
```

**Key Components**:
- New router: `/system/apps/`
- Data models for app information
- Kafka producers for app data
- Schema validation for platform-specific fields

### Device Metadata Management

```
Device → Metadata Endpoint → Flexible Validation → Kafka → Storage
```

**Metadata Types**:
- Device capabilities (`device_capabilities`)
- Hardware specifications (`hardware_specs`)
- Software configuration (`software_config`)
- Custom attributes (`custom_*`)

## 🔧 Configuration Changes

### New Environment Variables

```bash
# Topic Management
export LOOM_KAFKA_AUTO_CREATE_TOPICS=true
export LOOM_KAFKA_DEFAULT_PARTITIONS=3
export LOOM_KAFKA_DEFAULT_REPLICATION_FACTOR=1

# New Topics
export LOOM_TOPIC_DEVICE_SYSTEM_APPS_MACOS="device.system.apps.macos.raw"
export LOOM_TOPIC_DEVICE_SYSTEM_APPS_ANDROID="device.system.apps.android.raw"
export LOOM_TOPIC_DEVICE_METADATA="device.metadata.raw"

# App Monitoring
export LOOM_APP_MONITORING_MAX_APPS_PER_REQUEST=100
export LOOM_APP_MONITORING_ENABLED=true
```

### Helm Chart Updates
- Add new environment variables to values.yaml
- Update ConfigMap template
- Add new topic configurations

## 🧪 Testing Strategy

### Unit Tests
- Kafka topic creation logic
- App monitoring data validation
- Device metadata handling
- Error scenarios and edge cases

### Integration Tests
- End-to-end topic creation on startup
- App monitoring data flow through Kafka
- Metadata storage and retrieval
- Multiple concurrent app monitoring requests

### Load Testing
- App monitoring with large application lists
- Concurrent metadata updates
- Topic creation under load

## 📈 Success Metrics

### Functional Metrics
- ✅ All required topics created automatically on startup
- ✅ App monitoring data successfully ingested and validated
- ✅ Device metadata stored with flexible schema support
- ✅ Zero manual topic creation required for development

### Performance Metrics
- Topic creation time < 10 seconds on startup
- App monitoring endpoint response time < 500ms
- Support for 100+ apps per monitoring request
- Metadata ingestion rate > 1000 events/minute

### Quality Metrics
- 100% test coverage for new features
- Zero schema validation failures in production
- Documentation completeness score > 95%

## 🚀 Deployment Plan

### Phase 1: Infrastructure (Week 1)
1. Implement Kafka topic auto-creation
2. Add new environment variables
3. Update Helm charts and configuration
4. Deploy to development environment

### Phase 2: App Monitoring (Week 2)
1. Implement macOS app monitoring endpoint
2. Add Android app monitoring support
3. Create JSON schemas for validation
4. Add comprehensive testing

### Phase 3: Metadata & Documentation (Week 2)
1. Implement device metadata endpoint
2. Update integration guide
3. Add SDK examples
4. Performance testing and optimization

## 🔄 Definition of Done

### Code Complete
- [ ] All endpoints implemented with proper validation
- [ ] Kafka topic auto-creation working reliably
- [ ] Comprehensive unit and integration tests
- [ ] Error handling and logging implemented

### Documentation
- [ ] Integration guide updated with new endpoints
- [ ] API documentation includes new schemas
- [ ] README updated with new environment variables
- [ ] CLAUDE.md updated with new commands

### Quality Assurance
- [ ] All tests passing (unit, integration, load)
- [ ] Code review completed
- [ ] Security review for new endpoints
- [ ] Performance benchmarks meet targets

### Deployment Ready
- [ ] Helm charts updated and tested
- [ ] Environment variables documented
- [ ] Deployment guide includes new features
- [ ] Rollback plan documented

## 🔗 Dependencies

### Internal
- Existing Kafka infrastructure
- Current API framework and validation
- Helm chart configuration system

### External
- aiokafka library for admin operations
- JSON Schema validation library
- Kubernetes cluster with sufficient resources

## 🎯 Sprint Retrospective Items

### Questions to Address
1. How can we make topic management even more robust?
2. What additional app monitoring metrics would be valuable?
3. How should we handle schema evolution for metadata?
4. What performance optimizations are needed for large app lists?

---

**Sprint Start**: 2024-06-21
**Sprint End**: 2024-07-05
**Sprint Master**: Development Team
**Product Owner**: System Architecture Team
