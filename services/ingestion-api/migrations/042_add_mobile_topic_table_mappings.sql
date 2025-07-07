-- Migration 042: Add Mobile Topic-to-Table Mappings
-- Purpose: Configure topic-to-table mappings for all mobile data sources
-- This ensures data flows from Kafka topics to the appropriate database tables

-- =====================================================
-- DEVICE IMAGE AND SCREENSHOT MAPPINGS
-- =====================================================

-- Configure topic-to-table for camera images
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.image.camera.raw', 'device_image_camera_raw', 'device_id, timestamp', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for camera images
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.image.camera.raw', 'device_image_camera_raw', 'device_id', 'device_id', 'string', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.image.camera.raw', 'device_image_camera_raw', 'image_data', 'image_data', 'string', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'format', 'format', 'string', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'width', 'width', 'integer', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'height', 'height', 'integer', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'file_size', 'file_size_bytes', 'bigint', true),
    ('device.image.camera.raw', 'device_image_camera_raw', 'camera_type', 'source', 'string', false),
    ('device.image.camera.raw', 'device_image_camera_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Configure topic-to-table for screenshots (using same table as camera)
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.image.screenshot.raw', 'device_image_camera_raw', 'device_id, timestamp', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for screenshots
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'device_id', 'device_id', 'string', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'image_data', 'image_data', 'string', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'format', 'format', 'string', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'width', 'width', 'integer', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'height', 'height', 'integer', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'file_size', 'file_size_bytes', 'bigint', true),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'camera_type', 'source', 'string', false),
    ('device.image.screenshot.raw', 'device_image_camera_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- SENSOR DATA MAPPINGS
-- =====================================================

-- Configure topic-to-table for temperature sensor
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'device_id, timestamp', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add field mappings for temperature sensor
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'device_id', 'device_id', 'string', true),
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'data.temperature_celsius', 'temperature', 'float', true),
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'data.sensor_location', 'sensor_location', 'string', false),
    ('device.sensor.temperature.raw', 'device_sensor_temperature_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Configure topic-to-table for barometer sensor
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'device_id, timestamp', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add field mappings for barometer sensor
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'device_id', 'device_id', 'string', true),
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'data.pressure_hpa', 'pressure', 'float', true),
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'data.altitude_meters', 'altitude', 'float', false),
    ('device.sensor.barometer.raw', 'device_sensor_barometer_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- NETWORK DATA MAPPINGS
-- =====================================================

-- Configure topic-to-table for WiFi network data
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.network.wifi.raw', 'device_network_wifi_raw', 'device_id, timestamp', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for WiFi network data
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'device_id', 'device_id', 'string', true),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'data.ssid', 'ssid', 'string', false),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'data.bssid', 'bssid', 'string', false),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'data.signal_strength', 'signal_strength', 'integer', false),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'data.frequency', 'frequency', 'integer', false),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'data.is_connected', 'is_connected', 'boolean', true),
    ('device.network.wifi.raw', 'device_network_wifi_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Configure topic-to-table for Bluetooth network data
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'device_id, timestamp, device_address', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for Bluetooth network data
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'device_id', 'device_id', 'string', true),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'data.device_name', 'device_name', 'string', false),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'data.device_address', 'device_address', 'string', true),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'data.device_type', 'device_type', 'string', false),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'data.rssi', 'rssi', 'integer', false),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'data.is_connected', 'is_connected', 'boolean', false),
    ('device.network.bluetooth.raw', 'device_network_bluetooth_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- OS EVENTS AND SYSTEM MONITORING MAPPINGS
-- =====================================================

-- Configure topic-to-table for OS system events
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('os.events.system.raw', 'os_events_system_raw', 'device_id, timestamp', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add field mappings for OS system events
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.system.raw', 'os_events_system_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.system.raw', 'os_events_system_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'event_category', 'event_category', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'severity', 'severity', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'description', 'description', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Configure topic-to-table for app lifecycle events
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'device_id, timestamp, app_identifier', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add field mappings for app lifecycle events
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_identifier', 'app_identifier', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_name', 'app_name', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'duration_seconds', 'duration_seconds', 'integer', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Configure topic-to-table for Android app monitoring
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'device_id, timestamp, package_name', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for Android app monitoring
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'device_id', 'device_id', 'string', true),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'running_applications[].package_name', 'package_name', 'string', true),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'running_applications[].name', 'app_name', 'string', true),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'running_applications[].active', 'is_foreground', 'boolean', true),
    ('device.system.apps.android.raw', 'device_system_apps_android_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- HEALTH DATA MAPPINGS
-- =====================================================

-- Configure topic-to-table for step count data
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.health.steps.raw', 'device_health_steps_raw', 'device_id, timestamp', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for step count data
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.health.steps.raw', 'device_health_steps_raw', 'device_id', 'device_id', 'string', true),
    ('device.health.steps.raw', 'device_health_steps_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.health.steps.raw', 'device_health_steps_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.health.steps.raw', 'device_health_steps_raw', 'data.step_count', 'step_count', 'integer', true),
    ('device.health.steps.raw', 'device_health_steps_raw', 'data.duration_minutes', 'duration_minutes', 'integer', false),
    ('device.health.steps.raw', 'device_health_steps_raw', 'data.distance_meters', 'distance_meters', 'float', false),
    ('device.health.steps.raw', 'device_health_steps_raw', 'data.calories_burned', 'calories_burned', 'float', false),
    ('device.health.steps.raw', 'device_health_steps_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- AUDIO DATA MAPPINGS
-- =====================================================

-- Configure topic-to-table for audio data
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('device.audio.raw', 'device_audio_raw', 'device_id, timestamp, chunk_number', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add field mappings for audio data
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.audio.raw', 'device_audio_raw', 'device_id', 'device_id', 'string', true),
    ('device.audio.raw', 'device_audio_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.audio.raw', 'device_audio_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.audio.raw', 'device_audio_raw', 'chunk_number', 'chunk_number', 'integer', true),
    ('device.audio.raw', 'device_audio_raw', 'data', 'audio_data', 'string', true),
    ('device.audio.raw', 'device_audio_raw', 'format', 'format', 'string', true),
    ('device.audio.raw', 'device_audio_raw', 'sample_rate', 'sample_rate', 'integer', true),
    ('device.audio.raw', 'device_audio_raw', 'channels', 'channels', 'integer', true),
    ('device.audio.raw', 'device_audio_raw', 'duration_ms', 'duration_ms', 'integer', true),
    ('device.audio.raw', 'device_audio_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Display the newly configured topic-to-table mappings
SELECT
    ttc.topic_name,
    ttc.table_name,
    ttc.upsert_key,
    ttc.conflict_strategy,
    COUNT(tfm.id) as field_mappings_count
FROM topic_table_configs ttc
LEFT JOIN topic_field_mappings tfm ON ttc.topic_name = tfm.topic_name
WHERE ttc.topic_name IN (
    'device.image.camera.raw',
    'device.image.screenshot.raw',
    'device.sensor.temperature.raw',
    'device.sensor.barometer.raw',
    'device.network.wifi.raw',
    'device.network.bluetooth.raw',
    'os.events.system.raw',
    'os.events.app_lifecycle.raw',
    'device.system.apps.android.raw',
    'device.health.steps.raw',
    'device.audio.raw'
)
GROUP BY ttc.topic_name, ttc.table_name, ttc.upsert_key, ttc.conflict_strategy
ORDER BY ttc.topic_name;

-- Check which mobile-related topics still need configuration
SELECT
    kt.topic_name,
    kt.category,
    kt.source,
    kt.datatype,
    CASE
        WHEN ttc.table_name IS NOT NULL THEN 'Configured'
        ELSE 'Not Configured'
    END as db_status
FROM kafka_topics kt
LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
WHERE kt.topic_name LIKE 'device.%'
   OR kt.topic_name LIKE 'os.events.%'
   OR kt.topic_name LIKE 'digital.%'
ORDER BY db_status DESC, kt.topic_name;