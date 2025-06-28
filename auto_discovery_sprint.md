# Auto-Discovery Implementation Plan for Pipeline Monitor

## Overview
This document outlines the implementation of auto-discovery mechanisms that automatically detect Kafka topics, services, and their relationships, focusing on properly mapping the audio pipeline flow (raw → VAD → speech-to-text → DB) and integrating service health monitoring.

## Phase 1: Enhance Kafka Auto-Discovery

### 1. Update KafkaClient (`pipeline-monitor-api/src/kafka/client.ts`)
- Add method to get topic configurations (partitions, retention, replication)
- Add method to get consumer group details with lag information
- Add method to discover topic relationships based on consumer subscriptions

### 2. Enhance Pipeline Builder (`pipeline-monitor-api/src/services/pipelineBuilder.ts`)
- Implement intelligent topic relationship detection
- Add consumer group to topic mapping
- Create automatic flow detection for audio pipeline:
  - `device.audio.raw` → `silero-vad-consumer` → `media.audio.vad_filtered`
  - `media.audio.vad_filtered` → `parakeet-tdt-consumer` → `media.text.transcribed.words`
  - All processed data → `kafka-to-db-consumer` → TimescaleDB

## Phase 2: Service Discovery via Kubernetes API

### 3. Create Kubernetes Service Discovery (`pipeline-monitor-api/src/services/k8sDiscovery.ts`)
- Query Kubernetes API for deployments with specific labels
- Extract service metadata from pod annotations/labels
- Get health endpoint information from probe configurations
- Monitor pod status and resource usage

### 4. Add Service Registry Pattern (`pipeline-monitor-api/src/services/serviceRegistry.ts`)
- Create in-memory registry for discovered services
- Track service capabilities (input/output topics, processing type)
- Store health endpoint URLs
- Implement heartbeat tracking

## Phase 3: Health Monitoring Integration

### 5. Create Health Monitor Service (`pipeline-monitor-api/src/services/healthMonitor.ts`)
- Poll service health endpoints (/healthz, /readyz)
- Track service uptime and response times
- Monitor Kafka consumer lag
- Calculate service dependencies health score

### 6. Update Routes (`pipeline-monitor-api/src/routes/kafka.ts`)
- Add `/api/kafka/discover/all` endpoint for complete auto-discovery
- Add `/api/services/health` endpoint for aggregated health status
- Add `/api/services/registry` endpoint for discovered services

## Phase 4: Frontend Integration

### 7. Update Pipeline Monitor UI (`pipeline-monitor/src/App.tsx`)
- Add service health indicators to processor nodes
- Show consumer lag on edges
- Add health status colors (green/yellow/red)
- Display discovered vs configured indicators

### 8. Create Service Health Component (`pipeline-monitor/src/components/ServiceHealth.tsx`)
- Show detailed health metrics
- Display resource usage
- Show processing rates
- Add health history graphs

## Phase 5: Audio Pipeline Specific Enhancements

### 9. Audio Flow Mapping
Ensure complete audio pipeline is discovered:
```
Ingestion API → device.audio.raw
             ↓
Silero VAD → media.audio.vad_filtered
             ↓
Parakeet TDT → media.text.transcribed.words
             ↓
DB Consumer → TimescaleDB (audio_transcriptions table)
```
- Add special handling for audio chunk sequencing
- Track processing latency at each stage

### 10. Add Trace ID Tracking
- Follow trace_id through the entire pipeline
- Show message flow visualization
- Calculate end-to-end latency

## Implementation Details

### New Auto-Discovery API Endpoints:

```typescript
GET /api/kafka/discover/all
Response: {
  topics: [...],
  consumers: [...],
  services: [...],
  flows: [
    {
      source: "device.audio.raw",
      processor: "silero-vad",
      destination: "media.audio.vad_filtered",
      health: "healthy",
      lag: 0
    }
  ]
}

GET /api/services/health
Response: {
  services: [
    {
      name: "silero-vad",
      status: "healthy",
      uptime: 3600,
      lastCheck: "2024-01-26T10:00:00Z",
      endpoints: {
        health: "http://silero-vad:8000/healthz",
        ready: "http://silero-vad:8000/readyz"
      },
      resources: {
        cpu: "45%",
        memory: "2.1GB"
      }
    }
  ]
}
```

### Kubernetes Label Convention:
```yaml
labels:
  app: service-name
  component: ai-processing
  loom.pipeline/input-topics: "device.audio.raw"
  loom.pipeline/output-topics: "media.audio.vad_filtered"
  loom.pipeline/processor-type: "vad"
```

## Benefits
- Zero configuration required for new services
- Real-time health monitoring
- Automatic pipeline visualization
- Accurate data flow tracking
- Early detection of processing bottlenecks

## Quick Wins (Immediate Implementation)

### 1. Kafka Topic Auto-Discovery
- Query Kafka for all topics
- Show unmapped topics in UI
- Basic consumer group mapping

### 2. Environment Variable Parsing
- Read K8s pod env vars
- Extract topic names from config
- Build basic relationships

### 3. Health Check Integration
- Query service /healthz endpoints
- Show live service status
- Alert on unhealthy services

## Timeline
- Week 1: Kafka metadata discovery and enhanced pipeline builder
- Week 2: Service registry and Kubernetes integration
- Week 3: Health monitoring and frontend updates
- Week 4: Testing, optimization, and documentation