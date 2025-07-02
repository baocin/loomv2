-- TimescaleDB Hypertable Analytics
-- Provides detailed analysis of hypertables including data distribution over time

-- Hypertable overview
SELECT 
    h.schema_name,
    h.table_name,
    h.num_dimensions,
    count(c.id) AS num_chunks,
    pg_size_pretty(pg_total_relation_size(format('%I.%I', h.schema_name, h.table_name)::regclass)) AS total_size
FROM _timescaledb_catalog.hypertable h
LEFT JOIN _timescaledb_catalog.chunk c ON h.id = c.hypertable_id
GROUP BY h.schema_name, h.table_name, h.num_dimensions
ORDER BY pg_total_relation_size(format('%I.%I', h.schema_name, h.table_name)::regclass) DESC; 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    ch.schema_name || '.' || ch.table_name AS chunk_name,
    pg_size_pretty(pg_relation_size(format('%I.%I', ch.schema_name, ch.table_name)::regclass)) AS chunk_size,
    ch.creation_time,
    CASE 
        WHEN ch.compressed_chunk_id IS NOT NULL THEN 'Compressed'
        ELSE 'Uncompressed'
    END AS compression_status
FROM _timescaledb_catalog.hypertable ht
JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id
WHERE NOT ch.dropped
ORDER BY ht.table_name, ch.creation_time DESC
LIMIT 20; 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    count(ch.id) AS total_chunks,
    count(CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN 1 END) AS compressed_chunks,
    ROUND(100.0 * count(CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN 1 END)::numeric / 
          NULLIF(count(ch.id), 0), 2) AS compression_rate_pct
FROM _timescaledb_catalog.hypertable ht
LEFT JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id AND NOT ch.dropped
GROUP BY ht.schema_name, ht.table_name
HAVING count(ch.id) > 0
ORDER BY compression_rate_pct DESC; 
    tablename,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = tablename 
            AND column_name = 'timestamp'
        ) THEN 'Has timestamp column'
        ELSE 'No timestamp column'
    END AS timestamp_status,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'device_audio_raw',
        'device_sensor_gps_raw',
        'device_sensor_accelerometer_raw',
        'device_health_heartrate_raw',
        'media_text_transcribed_words',
        'external_email_events_raw',
        'external_calendar_events_raw'
    )
ORDER BY tablename;