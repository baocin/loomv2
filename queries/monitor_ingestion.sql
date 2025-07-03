-- Real-time monitoring query for data ingestion
-- Run this repeatedly to monitor kafka-to-db consumer progress

-- Current ingestion rates (last 5 minutes)
WITH recent_data AS (
    SELECT 'device_audio_raw' as table_name, COUNT(*) as count_last_5min
    FROM device_audio_raw
    WHERE created_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 'device_sensor_accelerometer_raw', COUNT(*)
    FROM device_sensor_accelerometer_raw
    WHERE created_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 'device_sensor_gps_raw', COUNT(*)
    FROM device_sensor_gps_raw
    WHERE created_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 'device_network_wifi_raw', COUNT(*)
    FROM device_network_wifi_raw
    WHERE created_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 'twitter_posts', COUNT(*)
    FROM twitter_posts
    WHERE created_at > NOW() - INTERVAL '5 minutes'
    UNION ALL
    SELECT 'media_audio_voice_segments_raw', COUNT(*)
    FROM media_audio_voice_segments_raw
    WHERE created_at > NOW() - INTERVAL '5 minutes'
),
total_counts AS (
    SELECT 'device_audio_raw' as table_name, COUNT(*) as total_count
    FROM device_audio_raw
    UNION ALL
    SELECT 'device_sensor_accelerometer_raw', COUNT(*)
    FROM device_sensor_accelerometer_raw
    UNION ALL
    SELECT 'device_sensor_gps_raw', COUNT(*)
    FROM device_sensor_gps_raw
    UNION ALL
    SELECT 'device_network_wifi_raw', COUNT(*)
    FROM device_network_wifi_raw
    UNION ALL
    SELECT 'twitter_posts', COUNT(*)
    FROM twitter_posts
    UNION ALL
    SELECT 'media_audio_voice_segments_raw', COUNT(*)
    FROM media_audio_voice_segments_raw
)
SELECT
    t.table_name,
    t.total_count,
    COALESCE(r.count_last_5min, 0) as last_5min,
    COALESCE(r.count_last_5min * 12, 0) as est_per_hour,
    CASE
        WHEN COALESCE(r.count_last_5min, 0) = 0 THEN '⏸️  Stopped'
        WHEN r.count_last_5min < 10 THEN '🐌 Slow'
        WHEN r.count_last_5min < 100 THEN '▶️  Active'
        ELSE '🚀 Fast'
    END as ingestion_status
FROM total_counts t
LEFT JOIN recent_data r ON t.table_name = r.table_name
ORDER BY t.total_count DESC;

-- Show latest entries to verify data freshness
SELECT
    'device_audio_raw' as table_name,
    MAX(timestamp) as latest_data,
    AGE(NOW(), MAX(timestamp)) as data_age
FROM device_audio_raw
UNION ALL
SELECT
    'device_sensor_accelerometer_raw',
    MAX(timestamp),
    AGE(NOW(), MAX(timestamp))
FROM device_sensor_accelerometer_raw
UNION ALL
SELECT
    'device_network_wifi_raw',
    MAX(timestamp),
    AGE(NOW(), MAX(timestamp))
FROM device_network_wifi_raw
UNION ALL
SELECT
    'twitter_posts',
    MAX(created_at),
    AGE(NOW(), MAX(created_at))
FROM twitter_posts
ORDER BY latest_data DESC NULLS LAST;

-- Summary dashboard
SELECT
    NOW() as report_time,
    (SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname = 'public') as total_tables,
    (SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname = 'public' AND n_live_tup > 0) as tables_with_data,
    (SELECT SUM(n_live_tup) FROM pg_stat_user_tables WHERE schemaname = 'public') as total_estimated_rows,
    (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size;
