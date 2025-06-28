# Loom v2 Shared Services

This directory contains shared microservices that provide common functionality across the Loom v2 platform. These services are designed to be reusable, scalable, and reduce code duplication.

## Services

### Priority 1 - Core Infrastructure

#### Schema Registry Service
- **Purpose**: Centralized JSON Schema validation and versioning
- **Port**: 8010
- **Features**:
  - Schema evolution tracking
  - Compatibility checking
  - REST API for schema operations
  - Caching layer
  - Documentation generation

#### Privacy Filter Service
- **Purpose**: PII detection, redaction, and GDPR compliance
- **Port**: 8011
- **Features**:
  - Real-time PII detection
  - Configurable redaction rules
  - Data anonymization
  - Audit logging
  - GDPR deletion workflows

#### Device Identity Service
- **Purpose**: Device UUID management and cross-platform linking
- **Port**: 8012
- **Features**:
  - UUIDv8 generation
  - Device fingerprinting
  - Cross-platform device correlation
  - Device metadata enrichment
  - Privacy-preserving tracking

#### Event Router
- **Purpose**: Intelligent Kafka message routing and transformation
- **Port**: 8013
- **Features**:
  - Topic mapping and transformation
  - Dead letter queue management
  - Message replay capabilities
  - Routing rule engine
  - Performance monitoring

### Priority 2 - Data Processing

#### Time Series Aggregator
- **Purpose**: Generic time-based data aggregation
- **Port**: 8020
- **Features**:
  - Configurable window functions
  - Multiple aggregation types
  - Late-arriving data handling
  - Kafka and TimescaleDB output
  - Real-time and batch processing

#### File Processing Service
- **Purpose**: Media and document processing
- **Port**: 8021
- **Features**:
  - Image thumbnail generation
  - Audio conversion and chunking
  - Document text extraction
  - Video frame extraction
  - Metadata extraction

#### Data Deduplication Service
- **Purpose**: Duplicate event detection and removal
- **Port**: 8022
- **Features**:
  - Configurable dedup windows
  - Fuzzy matching algorithms
  - Out-of-order data handling
  - Statistics tracking
  - Performance optimization

#### Context Enrichment Service
- **Purpose**: Add contextual metadata to events
- **Port**: 8023
- **Features**:
  - Location-to-place resolution
  - Time-based context detection
  - Weather data integration
  - Calendar event correlation
  - Configurable enrichment rules

### Priority 3 - Operations & Monitoring

#### Health Check Aggregator
- **Purpose**: Centralized health monitoring
- **Port**: 8030
- **Features**:
  - Service dependency tracking
  - Automated remediation
  - SLA monitoring
  - Incident correlation
  - Dashboard integration

#### Data Quality Monitor
- **Purpose**: Real-time data validation and quality assessment
- **Port**: 8031
- **Features**:
  - Schema compliance checking
  - Anomaly detection
  - Data completeness monitoring
  - Drift detection
  - Quality metrics dashboard

## Architecture Patterns

### Service Communication
- **REST APIs**: For synchronous operations
- **Kafka**: For asynchronous event processing
- **gRPC**: For high-performance internal communication
- **WebSockets**: For real-time updates

### Data Storage
- **Redis**: For caching and temporary data
- **PostgreSQL**: For metadata and configuration
- **TimescaleDB**: For time-series metrics
- **MinIO**: For large file storage

### Observability
- **Structured Logging**: JSON format with trace correlation
- **Metrics**: Prometheus-compatible metrics
- **Tracing**: Distributed tracing with correlation IDs
- **Health Checks**: Kubernetes-compatible health endpoints

## Development Guidelines

### Service Structure
```
service-name/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt (Python) or package.json (Node.js)
├── app/
│   ├── main.py (or index.js)
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── tests/
└── README.md
```

### Configuration
- Environment-based configuration
- Secrets managed via Kubernetes secrets
- Feature flags for gradual rollouts
- Health check endpoints
- Graceful shutdown handling

### Testing
- Unit tests with >80% coverage
- Integration tests with external dependencies
- Load testing for performance validation
- Contract testing for API compatibility
- End-to-end testing with real data

### Deployment
- Multi-stage Docker builds
- Health checks and readiness probes
- Resource limits and requests
- Horizontal pod autoscaling
- Blue-green deployment support

## Usage Examples

### Schema Registry
```python
# Validate data against schema
response = requests.post('http://schema-registry:8010/validate', json={
    'schema_name': 'device.sensor.gps.v1',
    'data': gps_reading_data
})
```

### Privacy Filter
```python
# Filter PII from data
response = requests.post('http://privacy-filter:8011/filter', json={
    'data': raw_data,
    'rules': ['email', 'phone', 'ssn']
})
```

### Device Identity
```python
# Link devices for same user
response = requests.post('http://device-identity:8012/link', json={
    'device_ids': ['uuid1', 'uuid2'],
    'confidence_score': 0.95
})
```

## Monitoring

Each service exposes:
- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics
- `/ready` - Readiness probe
- `/version` - Service version info

## Contributing

1. Follow the established patterns
2. Add comprehensive tests
3. Update documentation
4. Ensure security best practices
5. Test with multiple clients