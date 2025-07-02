-- Check recent data ingestion across all tables
-- Useful for monitoring if data is flowing correctly

-- Recent data summary for main tables
SELECT * FROM (
    SELECT 
        'device_audio_raw' as table_name,
        count(*) as records_last_hour,
        max(timestamp) as latest_timestamp,
        CASE 
            WHEN count(*) = 0 THEN '❌ No recent data'
            WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
            WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
            ELSE '❌ Stale'
        END as status
    FROM device_audio_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
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
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
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
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'device_health_heartrate_raw',
        count(*),
        max(timestamp),
        CASE 
            WHEN count(*) = 0 THEN '❌ No recent data'
            WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
            WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
            ELSE '❌ Stale'
        END
    FROM device_health_heartrate_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'media_text_transcribed_words',
        count(*),
        max(timestamp),
        CASE 
            WHEN count(*) = 0 THEN '❌ No recent data'
            WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
            WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
            ELSE '❌ Stale'
        END
    FROM media_text_transcribed_words
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'external_email_events_raw',
        count(*),
        max(timestamp),
        CASE 
            WHEN count(*) = 0 THEN '❌ No recent data'
            WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
            WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
            ELSE '❌ Stale'
        END
    FROM external_email_events_raw
    WHERE timestamp > now() - interval '1 hour'
    
    UNION ALL
    
    SELECT 
        'external_calendar_events_raw',
        count(*),
        max(timestamp),
        CASE 
            WHEN count(*) = 0 THEN '❌ No recent data'
            WHEN max(timestamp) > now() - interval '5 minutes' THEN '✅ Active'
            WHEN max(timestamp) > now() - interval '15 minutes' THEN '⚠️ Slow'
            ELSE '❌ Stale'
        END
    FROM external_calendar_events_raw
    WHERE timestamp > now() - interval '1 hour'
) recent_data
ORDER BY 
    CASE 
        WHEN records_last_hour > 0 THEN 0 
        ELSE 1 
    END,
    records_last_hour DESC;

