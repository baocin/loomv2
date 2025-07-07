-- Comprehensive Mobile Data Pipeline Status Check
-- This script checks the current status of mobile data ingestion

-- 1. Check recent API activity (last hour)
WITH api_endpoints AS (
    SELECT DISTINCT api_endpoint, topic_name 
    FROM topic_api_endpoints 
    WHERE api_endpoint LIKE '/sensor/%' 
       OR api_endpoint LIKE '/os-events/%'
       OR api_endpoint LIKE '/images/%'
)
SELECT 
    '=== API Endpoint to Topic Mapping ===' as section,
    api_endpoint,
    topic_name
FROM api_endpoints
ORDER BY api_endpoint;

-- 2. Check topic configurations
SELECT 
    '=== Topic Configuration Status ===' as section,
    kt.topic_name,
    kt.is_active as topic_active,
    COALESCE(ttc.table_name, 'NO TABLE') as target_table,
    COALESCE(ttc.is_active, false) as mapping_active,
    COUNT(DISTINCT tfm.id) as field_count
FROM kafka_topics kt
LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
LEFT JOIN topic_field_mappings tfm ON kt.topic_name = tfm.topic_name
WHERE kt.topic_name IN (
    'device.sensor.accelerometer.raw',
    'device.sensor.gps.raw',
    'device.network.wifi.raw',
    'device.state.power.raw',
    'os.events.system.raw'
)
GROUP BY kt.topic_name, kt.is_active, ttc.table_name, ttc.is_active
ORDER BY kt.topic_name;

-- 3. Check actual data in tables
SELECT 
    '=== Table Data Status ===' as section,
    table_name,
    total_count,
    recent_count,
    latest_timestamp,
    CASE 
        WHEN latest_timestamp > NOW() - INTERVAL '1 hour' THEN '✅ Active'
        WHEN latest_timestamp > NOW() - INTERVAL '24 hours' THEN '⚠️ Stale'
        WHEN latest_timestamp IS NOT NULL THEN '❌ Very Stale'
        ELSE '❌ No Data'
    END as status
FROM (
    SELECT 
        'device_network_wifi_raw' as table_name,
        (SELECT COUNT(*) FROM device_network_wifi_raw) as total_count,
        (SELECT COUNT(*) FROM device_network_wifi_raw WHERE timestamp > NOW() - INTERVAL '1 hour') as recent_count,
        (SELECT MAX(timestamp) FROM device_network_wifi_raw) as latest_timestamp
    UNION ALL
    SELECT 
        'device_sensor_gps_raw',
        (SELECT COUNT(*) FROM device_sensor_gps_raw),
        (SELECT COUNT(*) FROM device_sensor_gps_raw WHERE timestamp > NOW() - INTERVAL '1 hour'),
        (SELECT MAX(timestamp) FROM device_sensor_gps_raw)
    UNION ALL
    SELECT 
        'device_sensor_accelerometer_raw',
        (SELECT COUNT(*) FROM device_sensor_accelerometer_raw),
        (SELECT COUNT(*) FROM device_sensor_accelerometer_raw WHERE timestamp > NOW() - INTERVAL '1 hour'),
        (SELECT MAX(timestamp) FROM device_sensor_accelerometer_raw)
    UNION ALL
    SELECT 
        'device_state_power_raw',
        (SELECT COUNT(*) FROM device_state_power_raw),
        (SELECT COUNT(*) FROM device_state_power_raw WHERE timestamp > NOW() - INTERVAL '1 hour'),
        (SELECT MAX(timestamp) FROM device_state_power_raw)
    UNION ALL
    SELECT 
        'os_events_system_raw',
        (SELECT COUNT(*) FROM os_events_system_raw),
        (SELECT COUNT(*) FROM os_events_system_raw WHERE timestamp > NOW() - INTERVAL '1 hour'),
        (SELECT MAX(timestamp) FROM os_events_system_raw)
) t
ORDER BY total_count DESC;

-- 4. Check consumer configurations
SELECT 
    '=== Consumer Configuration ===' as section,
    service_name,
    is_active,
    array_length(subscribed_topics, 1) as topic_count,
    updated_at
FROM consumer_configurations
WHERE service_name IN ('kafka-to-db-consumer', 'generic-kafka-to-db-consumer')
ORDER BY service_name;

-- 5. Current time for reference
SELECT 
    '=== Current Time ===' as section,
    NOW() as current_time;