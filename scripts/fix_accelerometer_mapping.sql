-- Fix accelerometer field mappings to match actual message format
-- The mobile app sends x, y, z at the root level, not under data

-- First, delete the incorrect mappings
DELETE FROM topic_field_mappings 
WHERE topic_name = 'device.sensor.accelerometer.raw'
AND source_field_path IN ('data.x', 'data.y', 'data.z');

-- Update the existing mappings if needed, or insert new ones
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'x', 'x', 'float', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'y', 'y', 'float', true),
    ('device.sensor.accelerometer.raw', 'device_sensor_accelerometer_raw', 'z', 'z', 'float', true)
ON CONFLICT (topic_name, source_field_path, target_column) 
DO UPDATE SET 
    data_type = EXCLUDED.data_type,
    is_required = EXCLUDED.is_required;

-- Verify the mappings
SELECT 
    source_field_path,
    target_column,
    data_type,
    is_required
FROM topic_field_mappings
WHERE topic_name = 'device.sensor.accelerometer.raw'
ORDER BY source_field_path;