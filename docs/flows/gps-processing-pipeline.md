# GPS Processing Pipeline

## Overview

The GPS processing pipeline handles location data from devices, enriches it with geocoding information, and detects presence in predefined georegions. This pipeline has been simplified to remove unnecessary enrichment steps while maintaining core functionality.

## Data Flow

```mermaid
graph LR
    A[device.sensor.gps.raw] --> B[kafka-to-db-consumer]
    A --> C[gps-geocoding-consumer]
    C --> D[location.address.geocoded]
    D --> E[georegion-detector]
    E --> F[location.georegion.detected]
    D --> B
    F --> B
    B --> G[(PostgreSQL/TimescaleDB)]
```

## Components

### 1. GPS Data Ingestion
- **Topic**: `device.sensor.gps.raw`
- **Source**: Mobile devices via ingestion API
- **Data**: Raw GPS coordinates with accuracy, speed, bearing
- **Retention**: 30 days

### 2. Direct Database Storage
- **Service**: `kafka-to-db-consumer`
- **Table**: `device_sensor_gps_raw`
- **Purpose**: Store all raw GPS data for historical analysis
- **Features**: Hypertable with automatic compression after 30 days

### 3. Geocoding Service
- **Service**: `gps-geocoding-consumer`
- **Input**: `device.sensor.gps.raw`
- **Output**: `location.address.geocoded`
- **Provider**: OpenCage API
- **Features**:
  - Rate limiting (1 req/sec, 2500/day)
  - Local caching within 50m radius
  - Minimum 100m distance for new geocoding

### 4. Georegion Detection
- **Service**: `georegion-detector`
- **Input**: `location.address.geocoded`
- **Output**: `location.georegion.detected`
- **Features**:
  - Configurable georegions (home, work, custom)
  - Distance-based confidence scoring
  - Entry/exit time tracking (future enhancement)

### 5. Database Tables

#### device_sensor_gps_raw
```sql
- trace_id (PRIMARY KEY)
- device_id
- timestamp (PRIMARY KEY)
- latitude
- longitude
- altitude
- accuracy
- speed
- bearing
- provider
- metadata (JSONB)
```

#### location_address_geocoded
```sql
- trace_id (PRIMARY KEY)
- device_id
- timestamp (PRIMARY KEY)
- latitude
- longitude
- formatted_address
- city
- state
- country
- postal_code
- street
- house_number
- confidence
- geocoding_provider
- original_gps_trace_id
```

#### location_georegion_detected
```sql
- trace_id (PRIMARY KEY)
- device_id
- timestamp (PRIMARY KEY)
- georegion_id
- georegion_name
- georegion_type
- latitude
- longitude
- distance_to_center_meters
- confidence_score
- entry_time
- exit_time
- trigger_source
```

## Configuration

### Environment Variables
```bash
# Common
LOOM_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
LOOM_DATABASE_URL=postgresql://loom:loom@localhost:5432/loom

# Geocoding Service
LOOM_OPENCAGE_API_KEY=your_api_key
LOOM_MIN_DISTANCE_METERS=100.0
LOOM_CACHE_RADIUS_METERS=50.0

# Georegion Detection
LOOM_DETECTION_RADIUS_METERS=100.0
```

### Default Georegions
Georegions can be configured via environment variables or database. Default configuration includes:
- **Home**: 50m radius
- **Work**: 100m radius
- **Custom**: User-defined locations

## Deployment

All services are deployed as Kubernetes deployments with:
- Health check endpoints (`/healthz`, `/readyz`)
- Prometheus metrics (`/metrics`)
- Horizontal pod autoscaling based on CPU/memory
- Graceful shutdown handling

## Monitoring

### Metrics
- `gps_messages_processed_total` - Total GPS messages processed
- `geocoding_api_requests_total` - Geocoding API calls
- `georegion_detections_made_total` - Georegion detections
- `processing_duration_seconds` - Processing time histograms

### Alerts
- High error rate (>1%)
- Geocoding API quota exhaustion
- Processing lag > 5 minutes
- Service unavailability

## Future Enhancements

1. **State Tracking**: Track entry/exit times for georegions
2. **Dynamic Georegions**: Allow users to define custom georegions via API
3. **Prediction**: Use historical data to predict next location
4. **Clustering**: Automatically discover frequent locations
5. **Privacy**: Implement location fuzzing for sensitive areas