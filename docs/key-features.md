# Key Features and Architectural Insights

This document covers important architectural features and patterns in Loom v2 that may not be immediately obvious but are crucial for understanding and extending the system.

## Table of Contents
- [Kafka Service Registration and Discovery](#kafka-service-registration-and-discovery)
- [Docker Image Labeling and Traceability](#docker-image-labeling-and-traceability)
- [Pipeline Monitor Architecture](#pipeline-monitor-architecture)
- [Schema Management and Validation](#schema-management-and-validation)
- [Performance Optimizations](#performance-optimizations)
- [Development Workflow Enhancements](#development-workflow-enhancements)

## Kafka Service Registration and Discovery

### Automatic Service Discovery via Consumer Groups

Loom v2 uses Kafka's consumer group metadata as a service registry, eliminating the need for a separate service discovery system:

```yaml
# How it works:
1. Each service registers as a Kafka consumer group (e.g., 'silero-vad-consumer')
2. The Pipeline Monitor queries Kafka for active consumer groups
3. Services are automatically discovered based on their subscriptions
4. Health is determined by consumer lag and last heartbeat
```

### Consumer Group Naming Convention

```
<service-name>-consumer
```

Examples:
- `silero-vad-consumer` - Voice Activity Detection service
- `parakeet-tdt-consumer` - Speech-to-Text service
- `kafka-to-db-consumer` - Database persistence service

### Topic-Based Service Topology

The system automatically builds a service topology by analyzing:
- **Input Topics**: Topics a consumer group subscribes to
- **Output Topics**: Topics a service produces (inferred from patterns)
- **Data Flows**: Connections between services based on topic pub/sub

### Accessing Service Metadata

```bash
# List all consumer groups
kubectl exec -n loom-dev deployment/kafka -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Get consumer group details
kubectl exec -n loom-dev deployment/kafka -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group silero-vad-consumer --describe

# Via Pipeline Monitor API
curl http://localhost:8082/api/kafka/structure
```

## Docker Image Labeling and Traceability

### Git Commit Labels

Every Docker image built includes metadata for full traceability:

```dockerfile
# Labels added to all images
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.source="https://github.com/loomv2/loomv2" \
      com.loomv2.git.commit="${GIT_COMMIT}" \
      com.loomv2.git.branch="${GIT_BRANCH}"
```

### Building with Labels

```bash
# Automatic labeling via make
make dev-compose-build

# Or using the dedicated script
./scripts/docker-build-with-labels.sh

# Build specific service
make dev-compose-build SERVICE=ingestion-api
```

### Inspecting Image Metadata

```bash
# Show labels for all Loom images
make docker-labels

# Inspect specific service
make docker-labels SERVICE=ingestion-api

# Direct Docker command
docker inspect loom-ingestion-api:latest \
  --format '{{json .Config.Labels}}' | jq .
```

### Image Tagging Strategy

Images are dual-tagged for flexibility:
- `service-name:latest` - Always points to newest build
- `service-name:<git-short-hash>` - Immutable reference to specific commit

## Pipeline Monitor Architecture

### Comprehensive Structure Endpoint

The Pipeline Monitor API provides a complete view of the system at `/api/kafka/structure`:

```json
{
  "producers": [
    {
      "id": "ingestion-api",
      "label": "Ingestion API",
      "description": "Real-time data ingestion service",
      "outputTopics": ["device.audio.raw", "device.sensor.gps.raw", ...]
    }
  ],
  "topics": [
    {
      "name": "device.audio.raw",
      "category": "device",
      "dataType": "audio",
      "stage": "raw",
      "description": "Audio Raw"
    }
  ],
  "consumers": [
    {
      "groupId": "silero-vad-consumer",
      "label": "VAD Processor",
      "description": "Voice Activity Detection",
      "subscribedTopics": ["device.audio.raw"],
      "producesTopics": ["media.audio.vad_filtered"],
      "status": "Stable",
      "memberCount": 1
    }
  ],
  "flows": [
    {
      "source": "device.audio.raw",
      "processor": "silero-vad-consumer",
      "destination": "media.audio.vad_filtered",
      "health": "healthy",
      "lag": 0
    }
  ]
}
```

### Performance Optimization

Query intervals are optimized based on data volatility:

| Data Type | Refresh Interval | Stale Time | Rationale |
|-----------|-----------------|------------|-----------|
| Pipeline Flow | 5s | 4s | Core visualization data |
| Topic Metrics | 10s | 8s | Changes less frequently |
| Service Health | 20s | 15s | Health checks are expensive |
| Service Registry | 60s | 50s | Topology rarely changes |
| Auto Discovery | 30s | 25s | Service discovery is stable |

### Visual Pipeline Builder

The Pipeline Monitor automatically:
- Discovers services from Kafka metadata
- Builds visual topology from topic subscriptions
- Tracks data flow health via consumer lag
- Persists node positions in localStorage

## Schema Management and Validation

### Hierarchical Schema Organization

```
shared/schemas/
├── device/
│   ├── audio/raw/v1.json
│   ├── sensor/gps/v1.json
│   └── health/heartrate/v1.json
├── media/
│   └── audio/vad_filtered/v1.json
└── analysis/
    └── context/reasoning_chains/v1.json
```

### Schema Versioning Strategy

- **Path-based versioning**: `category/type/subtype/version.json`
- **Semantic versioning**: v1, v2, etc.
- **Backward compatibility**: Required within major versions
- **Runtime validation**: Cached schema validators

### Schema Discovery

```python
# Automatic schema discovery in ingestion-api
schema_path = f"{category}/{data_type}/{sub_type}/v{version}.json"
validator = SchemaValidator.get_validator(schema_path)
```

## Performance Optimizations

### Kafka Topic Configuration

High-volume topics use optimized settings:

```python
# From kafka_topics.py
"device.audio.raw": {
    "retention_days": 7,
    "compression": "lz4",  # Fast compression for audio
    "segment_ms": 3600000,  # 1-hour segments
}
```

### Database Optimization

PostgreSQL/TimescaleDB optimizations:
- Connection pooling with configurable limits
- Prepared statements for common queries
- Batch inserts for high-volume data
- Automatic retention policies

### Caching Strategy

Multiple caching layers:
1. **Schema validators**: Cached after first load
2. **Kafka metadata**: 5-minute TTL
3. **API responses**: Configurable per endpoint
4. **React Query**: Client-side stale-while-revalidate

## Development Workflow Enhancements

### Hot Reload Development

```bash
# Full stack with hot reload
make dev-up  # Tilt-based K8s development

# Or Docker Compose with file watching
make dev-compose-up
```

### Automated Topic Creation

Topics are automatically created on first use:
```python
# In kafka_producer.py
async def _ensure_topic_exists(self, topic: str):
    """Auto-create topic with optimal settings"""
```

### Mock Data Removal

All mock data generation has been removed. Services return empty lists when data sources are unavailable:

```python
# Old approach (removed)
return await self._get_mock_email_data()

# New approach
logger.warning("Gmail credentials not configured, returning empty list")
return []
```

### Pre-commit Hooks

Automated code quality enforcement:
- `black` - Code formatting
- `ruff` - Fast linting and import sorting
- `mypy` - Type checking
- `bandit` - Security scanning

### Comprehensive Testing

```bash
# Unit tests with coverage
make test

# Integration tests
make test-integration

# End-to-end pipeline test
make test-e2e

# Service-specific tests
cd services/ingestion-api && make test
```

## Advanced Features

### Remote Device Control

Bidirectional communication via Kafka:
```
device.command.keystroke.send → Device → device.response.command.status
device.command.screen.capture → Device → device.response.screen.capture
```

### Multi-Stage Processing Pipeline

Data flows through specialized stages:
1. **Raw ingestion**: `device.*` topics
2. **Filtering**: `media.*.filtered` topics
3. **Analysis**: `analysis.*` topics
4. **Persistence**: kafka-to-db-consumer

### Distributed Tracing

Trace IDs flow through the entire pipeline:
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "7d4c5f3e-2a1b-4e6d-8f9c-1234567890ab",
  "data": {...}
}
```

### Kubernetes Service Discovery

The system supports both Kafka-based and K8s-based discovery:
```typescript
// In k8sDiscovery.ts
async discoverServices(): Promise<ServiceInfo[]> {
  // Discovers services via K8s API
  // Complements Kafka-based discovery
}
```

## Best Practices

### Adding a New Service

1. Follow naming convention: `service-name-consumer`
2. Subscribe to input topics via Kafka consumer group
3. Produce to output topics with consistent schema
4. Include health endpoint at `/healthz`
5. Add Docker labels for traceability

### Topic Naming

Follow the hierarchical pattern:
```
<category>.<source>.<datatype>.<stage>
```

Examples:
- `device.audio.raw`
- `media.audio.vad_filtered`
- `analysis.context.reasoning_chains`

### Schema Evolution

1. Create new version file (e.g., `v2.json`)
2. Maintain backward compatibility
3. Update producers gradually
4. Migrate consumers with dual-version support
5. Deprecate old version after full migration

### Monitoring and Debugging

```bash
# Real-time pipeline monitoring
open http://localhost:3000

# Kafka topic inspection
make topics-list

# Service logs
make dev-compose-logs SERVICE=silero-vad

# Database queries
make db-connect
```

## Security Considerations

### Network Isolation

- Services communicate only via Kafka
- No direct service-to-service networking
- Database access restricted to kafka-to-db-consumer

### Authentication

- Device IDs validated at ingestion
- API keys for external services
- Kubernetes RBAC for service accounts

### Data Privacy

- PII handling in designated topics
- Configurable retention policies
- Audit logging for sensitive operations

---

This document serves as a guide to the less obvious but powerful features of Loom v2. For specific implementation details, refer to the service documentation and code comments.
