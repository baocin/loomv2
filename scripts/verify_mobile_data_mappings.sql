-- Verification Script: Mobile Data Source Mappings Status
-- This script shows which mobile data sources are properly configured
-- and which ones are missing topic-to-table mappings

-- =====================================================
-- 1. MOBILE DATA SOURCES FROM API ENDPOINTS
-- =====================================================

WITH mobile_endpoints AS (
    SELECT DISTINCT
        api_endpoint,
        topic_name
    FROM topic_api_endpoints
    WHERE api_endpoint IN (
        -- Images
        '/images/upload',
        '/images/screenshot',
        -- Sensors
        '/sensor/gps',
        '/sensor/accelerometer', 
        '/sensor/heartrate',
        '/sensor/power',
        '/sensor/temperature',
        '/sensor/barometer',
        '/sensor/wifi',
        '/sensor/bluetooth',
        -- Audio
        '/audio/upload',
        -- OS Events
        '/os-events/system',
        '/os-events/app-lifecycle',
        -- System
        '/system/apps/android',
        '/system/apps/android/usage'
    )
)
SELECT 
    me.api_endpoint,
    me.topic_name,
    COALESCE(ttc.table_name, 'NOT CONFIGURED') as target_table,
    COALESCE(ttc.conflict_strategy, '-') as conflict_strategy,
    COUNT(tfm.id) as field_mapping_count,
    CASE 
        WHEN ttc.table_name IS NULL THEN '❌ Missing'
        WHEN COUNT(tfm.id) = 0 THEN '⚠️  No field mappings'
        ELSE '✅ Configured'
    END as status
FROM mobile_endpoints me
LEFT JOIN topic_table_configs ttc ON me.topic_name = ttc.topic_name
LEFT JOIN topic_field_mappings tfm ON me.topic_name = tfm.topic_name
GROUP BY me.api_endpoint, me.topic_name, ttc.table_name, ttc.conflict_strategy
ORDER BY 
    CASE 
        WHEN ttc.table_name IS NULL THEN 1
        WHEN COUNT(tfm.id) = 0 THEN 2
        ELSE 3
    END,
    me.api_endpoint;

-- =====================================================
-- 2. TABLE EXISTENCE CHECK
-- =====================================================

SELECT 
    '--- Table Existence Check ---' as section;

WITH expected_tables AS (
    SELECT unnest(ARRAY[
        'device_audio_raw',
        'device_image_camera_raw',
        'device_sensor_gps_raw',
        'device_sensor_accelerometer_raw',
        'device_sensor_temperature_raw',
        'device_sensor_barometer_raw',
        'device_health_heartrate_raw',
        'device_state_power_raw',
        'device_network_wifi_raw',
        'device_network_bluetooth_raw',
        'os_events_system_raw',
        'os_events_app_lifecycle_raw',
        'device_system_apps_android_raw',
        'device_health_steps_raw'
    ]) as table_name
)
SELECT 
    et.table_name,
    CASE 
        WHEN t.table_name IS NOT NULL THEN '✅ Exists'
        ELSE '❌ Missing'
    END as table_status,
    COALESCE(h.hypertable_name, '-') as hypertable_status
FROM expected_tables et
LEFT JOIN information_schema.tables t 
    ON t.table_schema = 'public' 
    AND t.table_name = et.table_name
LEFT JOIN timescaledb_information.hypertables h
    ON h.hypertable_name = et.table_name
ORDER BY 
    CASE WHEN t.table_name IS NULL THEN 1 ELSE 2 END,
    et.table_name;

-- =====================================================
-- 3. DATA FLOW STATUS
-- =====================================================

SELECT 
    '--- Data Flow Pipeline Status ---' as section;

WITH pipeline_status AS (
    SELECT 
        kt.topic_name,
        kt.retention_days,
        COALESCE(tae.api_endpoint, 'No API endpoint') as api_endpoint,
        COALESCE(ttc.table_name, 'No table mapping') as table_name,
        COUNT(DISTINCT tfm.id) as field_mappings,
        CASE 
            WHEN tae.api_endpoint IS NULL THEN '1. No API'
            WHEN ttc.table_name IS NULL THEN '2. No Table'
            WHEN COUNT(DISTINCT tfm.id) = 0 THEN '3. No Fields'
            ELSE '4. Complete'
        END as pipeline_status
    FROM kafka_topics kt
    LEFT JOIN topic_api_endpoints tae ON kt.topic_name = tae.topic_name
    LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
    LEFT JOIN topic_field_mappings tfm ON kt.topic_name = tfm.topic_name
    WHERE kt.topic_name LIKE 'device.%' 
       OR kt.topic_name LIKE 'os.events.%'
    GROUP BY kt.topic_name, kt.retention_days, tae.api_endpoint, ttc.table_name
)
SELECT 
    topic_name,
    retention_days || ' days' as retention,
    api_endpoint,
    table_name,
    field_mappings,
    CASE pipeline_status
        WHEN '1. No API' THEN '❌ ' || pipeline_status
        WHEN '2. No Table' THEN '❌ ' || pipeline_status
        WHEN '3. No Fields' THEN '⚠️  ' || pipeline_status
        ELSE '✅ ' || pipeline_status
    END as status
FROM pipeline_status
ORDER BY pipeline_status, topic_name;

-- =====================================================
-- 4. SUMMARY STATISTICS
-- =====================================================

SELECT 
    '--- Summary Statistics ---' as section;

SELECT 
    COUNT(DISTINCT kt.topic_name) as total_device_topics,
    COUNT(DISTINCT tae.topic_name) as topics_with_api_endpoint,
    COUNT(DISTINCT ttc.topic_name) as topics_with_table_mapping,
    COUNT(DISTINCT CASE WHEN tfm.cnt > 0 THEN tfm.topic_name END) as topics_with_field_mappings,
    ROUND(100.0 * COUNT(DISTINCT ttc.topic_name) / COUNT(DISTINCT kt.topic_name), 1) || '%' as mapping_coverage
FROM kafka_topics kt
LEFT JOIN topic_api_endpoints tae ON kt.topic_name = tae.topic_name
LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
LEFT JOIN (
    SELECT topic_name, COUNT(*) as cnt 
    FROM topic_field_mappings 
    GROUP BY topic_name
) tfm ON kt.topic_name = tfm.topic_name
WHERE kt.topic_name LIKE 'device.%' 
   OR kt.topic_name LIKE 'os.events.%';