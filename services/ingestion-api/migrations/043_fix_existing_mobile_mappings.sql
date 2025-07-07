-- Migration 043: Fix Existing Mobile Mappings
-- Purpose: Update field mappings for GPS, Accelerometer, Heart Rate, and Power State
-- to match the actual data format sent by the mobile app

-- =====================================================
-- FIX GPS SENSOR MAPPINGS
-- =====================================================

-- Update GPS field mappings to use nested data structure
DELETE FROM topic_field_mappings WHERE topic_name = 'device.sensor.gps.raw';

INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'device_id', 'device_id', 'string', true),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.latitude', 'latitude', 'float', true),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.longitude', 'longitude', 'float', true),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.altitude', 'altitude', 'float', false),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.accuracy', 'accuracy', 'float', false),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.speed', 'speed', 'float', false),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'data.bearing', 'bearing', 'float', false),
    ('device.sensor.gps.raw', 'device_sensor_gps_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- FIX ACCELEROMETER SENSOR MAPPINGS
-- =====================================================

-- Update Accelerometer field mappings to use nested data structure
DELETE FROM topic_field_mappings WHERE topic_name = 'device.sensor.accelerometer.raw';

INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'device_id', 'device_id', 'string', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'data.x', 'x', 'float', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'data.y', 'y', 'float', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'data.z', 'z', 'float', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- FIX HEART RATE SENSOR MAPPINGS
-- =====================================================

-- Update Heart Rate field mappings to use nested data structure
DELETE FROM topic_field_mappings WHERE topic_name = 'device.health.heartrate.raw';

INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'device_id', 'device_id', 'string', true),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'data.heart_rate', 'heart_rate', 'integer', true),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'data.confidence', 'confidence', 'float', false),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'data.measurement_type', 'measurement_type', 'string', false),
    ('device.health.heartrate.raw', 'device_health_heartrate_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- FIX POWER STATE MAPPINGS
-- =====================================================

-- Update Power State field mappings to use nested data structure
DELETE FROM topic_field_mappings WHERE topic_name = 'device.state.power.raw';

INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.state.power.raw', 'device_state_power_raw', 'device_id', 'device_id', 'string', true),
    ('device.state.power.raw', 'device_state_power_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('device.state.power.raw', 'device_state_power_raw', 'schema_version', 'schema_version', 'string', false),
    ('device.state.power.raw', 'device_state_power_raw', 'data.battery_level', 'battery_level', 'integer', true),
    ('device.state.power.raw', 'device_state_power_raw', 'data.is_charging', 'is_charging', 'boolean', true),
    ('device.state.power.raw', 'device_state_power_raw', 'data.is_plugged_in', 'is_plugged_in', 'boolean', true),
    ('device.state.power.raw', 'device_state_power_raw', 'data.temperature_celsius', 'battery_temperature', 'float', false),
    ('device.state.power.raw', 'device_state_power_raw', 'data.voltage', 'voltage', 'float', false),
    ('device.state.power.raw', 'device_state_power_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- =====================================================
-- VERIFICATION QUERY
-- =====================================================

-- Display the updated mappings
SELECT
    ttc.topic_name,
    ttc.table_name,
    COUNT(tfm.id) as field_mappings_count
FROM topic_table_configs ttc
LEFT JOIN topic_field_mappings tfm ON ttc.topic_name = tfm.topic_name
WHERE ttc.topic_name IN (
    'device.sensor.gps.raw',
    'device.sensor.accelerometer.raw',
    'device.health.heartrate.raw',
    'device.state.power.raw'
)
GROUP BY ttc.topic_name, ttc.table_name
ORDER BY ttc.topic_name;