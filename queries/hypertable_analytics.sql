-- TimescaleDB Hypertable Analytics
-- Provides detailed analysis of hypertables including data distribution over time

-- Hypertable overview with chunk distribution
WITH hypertable_stats AS (
    SELECT 
        ht.schema_name,
        ht.table_name,
        ht.schema_name || '.' || ht.table_name AS full_name,
        count(DISTINCT ch.chunk_name) AS num_chunks,
        min(ch.range_start) AS oldest_data,
        max(ch.range_end) AS newest_data,
        sum(pg_relation_size(format('%I.%I', ch.chunk_schema, ch.chunk_name)::regclass)) AS total_bytes
    FROM _timescaledb_catalog.hypertable ht
    LEFT JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id
    LEFT JOIN _timescaledb_catalog.dimension d ON ht.id = d.hypertable_id
    WHERE d.column_name = 'timestamp'
    GROUP BY ht.schema_name, ht.table_name
)
SELECT 
    schema_name,
    table_name,
    num_chunks,
    pg_size_pretty(total_bytes) AS total_size,
    oldest_data::timestamp AS oldest_record,
    newest_data::timestamp AS newest_record,
    age(newest_data::timestamp, oldest_data::timestamp) AS data_span,
    ROUND(total_bytes::numeric / NULLIF(num_chunks, 0), 0) AS avg_chunk_bytes,
    pg_size_pretty(ROUND(total_bytes::numeric / NULLIF(num_chunks, 0), 0)::bigint) AS avg_chunk_size
FROM hypertable_stats
ORDER BY total_bytes DESC;

-- Data ingestion rate analysis (last 24 hours)
SELECT 
    '=== INGESTION RATES (Last 24 Hours) ===' AS info;

-- Device Audio Raw ingestion rate
SELECT 
    'device_audio_raw' AS table_name,
    count(*) AS records_24h,
    count(*) / 24.0 AS avg_per_hour,
    count(*) / 1440.0 AS avg_per_minute,
    pg_size_pretty(sum(pg_column_size(data))) AS data_size_24h
FROM device_audio_raw
WHERE timestamp > now() - interval '24 hours';

-- GPS data ingestion rate
SELECT 
    'device_sensor_gps_raw' AS table_name,
    count(*) AS records_24h,
    count(*) / 24.0 AS avg_per_hour,
    count(*) / 1440.0 AS avg_per_minute,
    avg(accuracy) AS avg_accuracy
FROM device_sensor_gps_raw
WHERE timestamp > now() - interval '24 hours';

-- Chunk information by hypertable
SELECT 
    '=== CHUNK DETAILS ===' AS info;

SELECT 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    ch.chunk_name,
    ch.range_start::timestamp AS chunk_start,
    ch.range_end::timestamp AS chunk_end,
    age(ch.range_end::timestamp, ch.range_start::timestamp) AS chunk_span,
    pg_size_pretty(pg_relation_size(format('%I.%I', ch.chunk_schema, ch.chunk_name)::regclass)) AS chunk_size
FROM _timescaledb_catalog.hypertable ht
JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id
JOIN _timescaledb_catalog.dimension d ON ht.id = d.hypertable_id
WHERE d.column_name = 'timestamp'
ORDER BY ht.table_name, ch.range_start DESC
LIMIT 20;

-- Compression statistics (if compression is enabled)
SELECT 
    '=== COMPRESSION STATS ===' AS info;

SELECT 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    count(DISTINCT ch.chunk_name) AS total_chunks,
    count(DISTINCT CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN ch.chunk_name END) AS compressed_chunks,
    ROUND(100.0 * count(DISTINCT CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN ch.chunk_name END) / 
          NULLIF(count(DISTINCT ch.chunk_name), 0), 2) AS compression_rate_pct
FROM _timescaledb_catalog.hypertable ht
LEFT JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id
GROUP BY ht.schema_name, ht.table_name
HAVING count(DISTINCT ch.chunk_name) > 0
ORDER BY compression_rate_pct DESC;