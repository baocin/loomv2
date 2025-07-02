-- TimescaleDB Hypertable Analytics
-- Provides detailed analysis of hypertables including data distribution over time

-- Check if TimescaleDB is installed
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        RAISE NOTICE 'TimescaleDB extension not installed. Hypertable analytics not available.';
    END IF;
END $$;

-- Hypertable overview (only runs if TimescaleDB is installed)
SELECT 
    h.schema_name,
    h.table_name,
    h.num_dimensions,
    count(DISTINCT c.chunk_name) AS num_chunks,
    pg_size_pretty(sum(pg_relation_size(format('%I.%I', c.chunk_schema, c.chunk_name)::regclass))) AS total_size
FROM _timescaledb_catalog.hypertable h
LEFT JOIN _timescaledb_catalog.chunk c ON h.id = c.hypertable_id
WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')
GROUP BY h.schema_name, h.table_name, h.num_dimensions
ORDER BY sum(pg_relation_size(format('%I.%I', c.chunk_schema, c.chunk_name)::regclass)) DESC;

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