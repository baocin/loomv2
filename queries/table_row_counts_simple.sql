-- Simple row count query for all tables in Loom database
-- This version is faster but less detailed

SELECT 
    schemaname AS schema,
    relname AS table_name,
    n_live_tup AS approximate_rows,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||relname)) AS total_size,
    CASE 
        WHEN last_vacuum IS NULL THEN 'Never'
        ELSE age(now(), last_vacuum)::text
    END AS last_vacuum_age,
    CASE 
        WHEN last_analyze IS NULL THEN 'Never'
        ELSE age(now(), last_analyze)::text
    END AS last_analyze_age
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;

-- For exact counts (slower but accurate)
-- Uncomment and run the queries below for specific tables:

/*
-- Example exact counts for common tables:
SELECT 'device_audio_raw' as table_name, count(*) as exact_count FROM device_audio_raw
UNION ALL
SELECT 'device_sensor_gps_raw', count(*) FROM device_sensor_gps_raw
UNION ALL
SELECT 'device_sensor_accelerometer_raw', count(*) FROM device_sensor_accelerometer_raw
UNION ALL
SELECT 'media_text_transcribed_words', count(*) FROM media_text_transcribed_words
UNION ALL
SELECT 'external_email_events_raw', count(*) FROM external_email_events_raw
UNION ALL
SELECT 'external_calendar_events_raw', count(*) FROM external_calendar_events_raw
ORDER BY exact_count DESC;
*/