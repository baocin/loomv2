# Pipeline Monitor - Accurate Data Flow Mapping

## Overview

The pipeline monitor now accurately represents the actual data flow in the system, showing:
1. All data sources (API endpoints, external fetchers, client applications)
2. All topics with their actual producers and consumers
3. The kafka-to-db consumer that persists data to TimescaleDB
4. Complete data lineage from source to storage

## Key Updates

### 1. Kafka-to-DB Consumer Visualization

Previously, topics were shown connecting directly to the database. Now:
- A "Kafka to DB Consumer" processor node is shown
- All 31 topics with table mappings connect to this consumer
- The consumer then connects to TimescaleDB
- This accurately represents how the `kafka-to-db-consumer` service works

### 2. External Data Sources

Added nodes for services that produce data but aren't API endpoints:
- **X Likes Fetcher** - Produces to `external.twitter.liked.raw`
- **Calendar Fetcher** - Produces to `external.calendar.events.raw`
- **Email Fetcher** - Produces to `external.email.events.raw`
- **Mobile Clients** - Produces to device sensor/health/OS event topics
- **Desktop Clients** - Produces to macOS monitoring topics

### 3. Complete Topic Coverage

The visualization now includes:
- **Raw topics** - Data as it enters the system
- **Processed topics** - Including filtered, enriched, geocoded, detected topics
- **Analysis topics** - Results from ML models and analysis services
- **Error topics** - Error messages from processing failures
- **Task topics** - Task queue topics

### 4. Accurate Producer/Consumer Mapping

The pipeline builder now:
1. Shows API endpoints from `topic_api_endpoints` table
2. Shows external producers for topics without API endpoints
3. Shows all processing stages from `pipeline_stages` table
4. Shows kafka-to-db consumer for all topics with `topic_table_configs`

## Data Flow Example: WiFi Network Data

1. **Source**: API endpoint `/sensor/wifi`
2. **Topic**: `device.network.wifi.raw`
3. **Consumer**: `kafka-to-db-consumer` (shown as processor node)
4. **Storage**: `device_network_wifi_raw` table in TimescaleDB

## Verification Queries

### Check topics with database tables:
```sql
SELECT topic_name, table_name
FROM topic_table_configs
ORDER BY topic_name;
```

### Check topics without defined producers:
```sql
SELECT kt.topic_name
FROM kafka_topics kt
LEFT JOIN pipeline_stage_topics pst
  ON kt.topic_name = pst.topic_name
  AND pst.topic_role = 'output'
LEFT JOIN topic_api_endpoints tae
  ON kt.topic_name = tae.topic_name
WHERE pst.topic_name IS NULL
  AND tae.topic_name IS NULL
  AND kt.is_active = true;
```

### Check kafka-to-db consumer configuration:
```sql
SELECT topic_name
FROM topic_table_configs
WHERE table_name IS NOT NULL;
-- All these topics should show connections to kafka-to-db consumer
```

## Visual Layout

The pipeline is organized left-to-right:
1. **Producers** (x=0): API endpoints and external sources
2. **Raw Topics** (x=300): Initial data topics
3. **Processors** (x=600): Services that transform data
4. **Processed Topics** (x=900): Transformed data
5. **Analysis Topics** (x=1200): ML/analysis results
6. **Kafka-to-DB** (x=1350): Database consumer
7. **TimescaleDB** (x=1500): Final storage

## Benefits

1. **Accurate Representation** - Shows actual data flow, not idealized
2. **Complete Coverage** - All 31 topics with DB tables are shown
3. **Service Discovery** - See which services process which topics
4. **Debugging Aid** - Understand why data might not be flowing
5. **Documentation** - Visual documentation of the system architecture
