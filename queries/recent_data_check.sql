-- Check recent data ingestion across all tables
-- Useful for monitoring if data is flowing correctly

-- Recent data summary for all hypertables
WITH recent_data AS (
    SELECT 
        'device_audio_raw' AS table_name,
        count(*) AS records_last_hour,
        max(timestamp) AS latest_timestamp,
        min(timestamp) AS hour_ago_timestamp
    FROM device_audio_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'device_sensor_gps_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM device_sensor_gps_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'device_sensor_accelerometer_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM device_sensor_accelerometer_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'device_health_heartrate_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM device_health_heartrate_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'device_state_power_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM device_state_power_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'media_text_transcribed_words',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM media_text_transcribed_words
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'external_email_events_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM external_email_events_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'external_calendar_events_raw',
        count(*),
        max(timestamp),
        min(timestamp)
    FROM external_calendar_events_raw
    WHERE timestamp > now() - interval '1 hour'
)
SELECT 
    table_name,
    records_last_hour,
    CASE 
        WHEN latest_timestamp IS NULL THEN 'No data'
        ELSE age(now(), latest_timestamp)::text
    END AS time_since_last_record,
    latest_timestamp,
    CASE 
        WHEN records_last_hour = 0 THEN '❌ No recent data'
        WHEN age(now(), latest_timestamp) < interval '5 minutes' THEN '✅ Active'
        WHEN age(now(), latest_timestamp) < interval '15 minutes' THEN '⚠️ Slow'
        ELSE '❌ Stale'
    END AS status
FROM recent_data
ORDER BY 
    CASE 
        WHEN records_last_hour > 0 THEN 0 
        ELSE 1 
    END,
    records_last_hour DESC;

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