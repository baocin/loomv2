-- Check recent data ingestion across all tables
-- Useful for monitoring if data is flowing correctly

-- Get list of tables that actually exist
DO $$
DECLARE
    table_exists boolean;
    result_text text := '';
BEGIN
    -- Check each table and provide summary
    CREATE TEMP TABLE IF NOT EXISTS recent_data_summary (
        table_name text,
        records_last_hour bigint,
        latest_timestamp timestamp,
        status text
    );
    
    -- Check device_audio_raw
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'device_audio_raw') THEN
        INSERT INTO recent_data_summary
        SELECT 
            'device_audio_raw',
            count(*),
            max(timestamp),
            CASE 
                WHEN count(*) = 0 THEN '❌ No recent data'
                WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
                WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
                ELSE '❌ Stale'
            END
        FROM device_audio_raw
        WHERE timestamp > now() - interval '1 hour';
    END IF;
    
    -- Check device_sensor_gps_raw
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'device_sensor_gps_raw') THEN
        INSERT INTO recent_data_summary
        SELECT 
            'device_sensor_gps_raw',
            count(*),
            max(timestamp),
            CASE 
                WHEN count(*) = 0 THEN '❌ No recent data'
                WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
                WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
                ELSE '❌ Stale'
            END
        FROM device_sensor_gps_raw
        WHERE timestamp > now() - interval '1 hour';
    END IF;
    
    -- Check device_sensor_accelerometer_raw
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'device_sensor_accelerometer_raw') THEN
        INSERT INTO recent_data_summary
        SELECT 
            'device_sensor_accelerometer_raw',
            count(*),
            max(timestamp),
            CASE 
                WHEN count(*) = 0 THEN '❌ No recent data'
                WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
                WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
                ELSE '❌ Stale'
            END
        FROM device_sensor_accelerometer_raw
        WHERE timestamp > now() - interval '1 hour';
    END IF;
END $$;

-- Show results
SELECT 
    table_name,
    records_last_hour,
    CASE 
        WHEN latest_timestamp IS NULL THEN 'No data'
        ELSE age(now(), latest_timestamp)::text
    END AS time_since_last,
    latest_timestamp,
    status
FROM recent_data_summary
ORDER BY 
    CASE 
        WHEN records_last_hour > 0 THEN 0 
        ELSE 1 
    END,
    records_last_hour DESC;

-- Clean up
DROP TABLE IF EXISTS recent_data_summary;

-- Alternative simpler query - check what tables exist
SELECT 
    '=== EXISTING TABLES WITH TIMESTAMP COLUMNS ===' AS info;

SELECT 
    t.table_schema,
    t.table_name,
    c.column_name AS timestamp_column
FROM information_schema.tables t
JOIN information_schema.columns c 
    ON t.table_schema = c.table_schema 
    AND t.table_name = c.table_name
WHERE t.table_schema = 'public'
    AND t.table_type = 'BASE TABLE'
    AND c.column_name IN ('timestamp', 'created_at', 'updated_at', 'ts')
    AND (t.table_name LIKE '%_raw' 
         OR t.table_name LIKE 'device_%' 
         OR t.table_name LIKE 'media_%'
         OR t.table_name LIKE 'external_%')
ORDER BY t.table_name;

-- Device activity summary
SELECT 
    '=== ACTIVE DEVICES (Last Hour) ===' AS info;

SELECT 
    device_id,
    count(DISTINCT table_source) AS active_streams,
    string_agg(DISTINCT table_source, ', ') AS data_types,
    max(last_seen) AS last_activity
FROM (
    SELECT device_id, 'audio' AS table_source, max(timestamp) AS last_seen
    FROM device_audio_raw
    WHERE timestamp > now() - interval '1 hour'
    GROUP BY device_id
    
    UNION ALL
    
    SELECT device_id, 'gps', max(timestamp)
    FROM device_sensor_gps_raw
    WHERE timestamp > now() - interval '1 hour'
    GROUP BY device_id
    
    UNION ALL
    
    SELECT device_id, 'accelerometer', max(timestamp)
    FROM device_sensor_accelerometer_raw
    WHERE timestamp > now() - interval '1 hour'
    GROUP BY device_id
) device_activity
GROUP BY device_id
ORDER BY active_streams DESC, last_activity DESC;