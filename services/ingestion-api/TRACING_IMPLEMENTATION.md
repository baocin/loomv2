# Distributed Tracing Implementation

This document describes the comprehensive distributed tracing system implemented for the Loom v2 ingestion API service.

## Overview

The tracing system provides end-to-end request correlation through:
- **Trace IDs**: Unique UUIDs that follow requests across all services
- **Services Encountered**: A list tracking which services have processed each request
- **Kafka Message Headers**: Trace information embedded in all message headers
- **Structured Logging**: All log entries automatically include trace context

## Implementation Components

### 1. Core Tracing Module (`app/tracing.py`)

#### TracingMiddleware
- **Purpose**: Automatically handles trace IDs for all HTTP requests
- **Behavior**:
  - Generates new trace ID if none provided
  - Preserves existing trace IDs from `X-Trace-ID` header
  - Maintains service chain from `X-Services-Encountered` header
  - Adds current service (`ingestion-api`) to the chain
  - Sets trace context for the entire request lifecycle

#### Context Management
```python
# Context variables for trace information
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")
services_encountered_context: ContextVar[list[str]] = ContextVar("services_encountered", default=[])
```

#### Utility Functions
- `get_trace_id()`: Retrieve current trace ID
- `get_services_encountered()`: Get current service chain
- `get_trace_context()`: Get complete trace context
- `add_service_to_trace(service_name)`: Add service to current trace
- `create_child_trace_context()`: Create new trace for child operations

### 2. Enhanced Data Models (`app/models.py`)

#### BaseMessage Enhancement
All Kafka messages now include:
```python
trace_id: str | None = Field(default=None, description="Distributed trace ID for request correlation")
services_encountered: list[str] = Field(default_factory=list, description="List of services that have processed this message")
```

#### Response Models
API responses include trace information:
```python
trace_id: str | None = Field(default=None, description="Distributed trace ID for request correlation")
services_encountered: list[str] = Field(default_factory=list, description="List of services that have processed this request")
```

### 3. Kafka Producer Integration (`app/kafka_producer.py`)

#### Message Headers
All Kafka messages include headers:
```python
headers = {
    "trace_id": trace_context.get("trace_id", "").encode("utf-8"),
    "services_encountered": ",".join(trace_context.get("services_encountered", [])).encode("utf-8"),
    "producer_service": "ingestion-api".encode("utf-8"),
}
```

#### Message Payload
Trace information is also embedded in message payloads for redundancy.

### 4. Enhanced Logging (`app/main.py`)

#### Automatic Trace Context
All log entries automatically include:
```python
def add_trace_context(logger, method_name, event_dict):
    """Add trace context to all log entries."""
    trace_context = get_trace_context()
    event_dict.update(trace_context)
    return event_dict
```

### 5. Endpoint Integration

#### All REST Endpoints
Every endpoint now:
1. Receives trace context from middleware
2. Adds trace information to messages before sending to Kafka
3. Returns trace information in responses
4. Logs with automatic trace context

#### Example Implementation (GPS Sensor)
```python
@router.post("/gps", status_code=status.HTTP_201_CREATED)
async def ingest_gps_data(gps_reading: GPSReading, request: Request, api_key: str = Depends(verify_api_key)) -> JSONResponse:
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        gps_reading.trace_id = trace_context.get("trace_id")
        gps_reading.services_encountered = trace_context.get("services_encountered", [])

        await kafka_producer.send_sensor_data(gps_reading, "gps")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": gps_reading.message_id,
                "topic": "device.sensor.gps.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )
```

#### WebSocket Handling
WebSocket connections create child trace contexts:
```python
# WebSocket messages don't go through middleware, so we create a new trace
websocket_trace_id = create_child_trace_context("", ["websocket-audio"])
audio_chunk.trace_id = websocket_trace_id
audio_chunk.services_encountered = ["websocket-audio", "ingestion-api"]
```

## Usage Examples

### 1. Client Request with Trace ID
```bash
curl -X POST "http://localhost:8000/sensor/gps" \
  -H "X-Trace-ID: 12345678-1234-4000-8000-123456789012" \
  -H "X-Services-Encountered: client-app,api-gateway" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "87654321-4321-8000-8000-210987654321",
    "recorded_at": "2024-01-15T10:30:00Z",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "accuracy": 5.0
  }'
```

### 2. Response with Trace Information
```json
{
  "status": "success",
  "message_id": "msg-uuid-here",
  "topic": "device.sensor.gps.raw",
  "trace_id": "12345678-1234-4000-8000-123456789012",
  "services_encountered": ["client-app", "api-gateway", "ingestion-api", "kafka-producer"]
}
```

### 3. Kafka Message with Trace Headers
```
Headers:
  trace_id: 12345678-1234-4000-8000-123456789012
  services_encountered: client-app,api-gateway,ingestion-api,kafka-producer
  producer_service: ingestion-api

Payload:
{
  "schema_version": "1.0",
  "device_id": "87654321-4321-8000-8000-210987654321",
  "recorded_at": "2024-01-15T10:30:00Z",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "accuracy": 5.0,
  "trace_id": "12345678-1234-4000-8000-123456789012",
  "services_encountered": ["client-app", "api-gateway", "ingestion-api", "kafka-producer"]
}
```

### 4. Log Entries with Trace Context
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "event": "GPS data ingested",
  "device_id": "87654321-4321-8000-8000-210987654321",
  "message_id": "msg-uuid-here",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "trace_id": "12345678-1234-4000-8000-123456789012",
  "services_encountered": ["client-app", "api-gateway", "ingestion-api", "kafka-producer"]
}
```

## Service Chain Tracking

The system automatically tracks which services have processed each request:

1. **Client Request**: `["client-app"]`
2. **Through API Gateway**: `["client-app", "api-gateway"]`
3. **Ingestion API**: `["client-app", "api-gateway", "ingestion-api"]`
4. **Kafka Producer**: `["client-app", "api-gateway", "ingestion-api", "kafka-producer"]`
5. **Future AI Services**: `["client-app", "api-gateway", "ingestion-api", "kafka-producer", "minicpm-vision", "mistral-reasoning"]`

## Testing

### Unit Tests (`tests/unit/test_tracing.py`)
Comprehensive test suite covering:
- Middleware functionality
- Trace ID generation and preservation
- Service chain tracking
- Kafka message integration
- Error handling with trace context
- Concurrent request isolation

### Verification Scripts
- `test_tracing_simple.py`: Core functionality verification
- `test_endpoint_tracing.py`: End-to-end endpoint testing

## Benefits

1. **Complete Request Tracing**: Follow requests from client to Kafka and beyond
2. **Debugging**: Easily identify which services processed problematic requests
3. **Performance Monitoring**: Track request latency across service boundaries
4. **Service Dependencies**: Understand actual service interaction patterns
5. **Operational Visibility**: Clear audit trail for all data processing

## Future Enhancements

1. **Metrics Integration**: Prometheus metrics tagged with trace information
2. **Jaeger/Zipkin Integration**: OpenTelemetry spans for detailed performance tracing
3. **Cross-Service Correlation**: Database and cache operations tagged with trace IDs
4. **AI Model Tracing**: Track which models processed which requests
5. **Batch Operation Tracing**: Parent-child trace relationships for batch processing

## Container Integration

When deploying in Docker containers, each service should:
1. Extract trace information from Kafka headers
2. Set trace context at service startup
3. Add its service name to the services_encountered list
4. Forward trace information to downstream services
5. Log with trace context for centralized logging systems

This implementation provides a solid foundation for distributed tracing across the entire Loom v2 microservices architecture.
