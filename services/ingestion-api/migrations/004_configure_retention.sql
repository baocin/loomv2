-- Migration 004: Configure Retention Policies
-- Description: Sets up automated data retention policies for all hypertables

-- Add retention policy for device_audio_raw (7 days)
SELECT add_retention_policy('device_audio_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Add retention policy for device_sensor_gps_raw (30 days)
SELECT add_retention_policy('device_sensor_gps_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policy for device_sensor_accelerometer_raw (30 days)
SELECT add_retention_policy('device_sensor_accelerometer_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policy for device_health_heartrate_raw (60 days)
SELECT add_retention_policy('device_health_heartrate_raw', INTERVAL '60 days', if_not_exists => TRUE);

-- Add retention policy for device_state_power_raw (30 days)
SELECT add_retention_policy('device_state_power_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policy for device_system_apps_macos_raw (30 days)
SELECT add_retention_policy('device_system_apps_macos_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policy for device_system_apps_android_raw (30 days)
SELECT add_retention_policy('device_system_apps_android_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policy for device_metadata_raw (90 days)
SELECT add_retention_policy('device_metadata_raw', INTERVAL '90 days', if_not_exists => TRUE);

-- View all configured policies
SELECT * FROM timescaledb_information.job_stats 
WHERE job_id IN (
    SELECT job_id FROM timescaledb_information.jobs 
    WHERE proc_name IN ('policy_retention', 'policy_compression')
);