-- Device activity summary (last hour)
SELECT 
    device_id,
    count(DISTINCT table_source) AS active_streams,
    string_agg(DISTINCT table_source, ', ' ORDER BY table_source) AS data_types,
    max(last_seen) AS last_activity,
    CASE 
        WHEN max(last_seen) > now() - interval '5 minutes' THEN '✅ Active'
        WHEN max(last_seen) > now() - interval '15 minutes' THEN '⚠️ Slow'
        ELSE '❌ Inactive'
    END AS status
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
    
    UNION ALL
    
    SELECT device_id, 'heartrate', max(timestamp)
    FROM device_health_heartrate_raw
    WHERE timestamp > now() - interval '1 hour'
    GROUP BY device_id
    
    UNION ALL
    
    SELECT device_id, 'power', max(timestamp)
    FROM device_state_power_raw
    WHERE timestamp > now() - interval '1 hour'
    GROUP BY device_id
) device_activity
GROUP BY device_id
ORDER BY active_streams DESC, last_activity DESC;