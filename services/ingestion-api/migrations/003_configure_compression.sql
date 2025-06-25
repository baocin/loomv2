-- Migration 003: Configure Compression Policies
-- Description: Sets up compression for all hypertables to achieve 90-95% storage savings

-- Configure compression for device_audio_raw (7 days retention)
ALTER TABLE device_audio_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('device_audio_raw', INTERVAL '1 day', if_not_exists => TRUE);

-- Configure compression for device_sensor_gps_raw (30 days retention)
ALTER TABLE device_sensor_gps_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('device_sensor_gps_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Configure compression for device_sensor_accelerometer_raw (30 days retention)
ALTER TABLE device_sensor_accelerometer_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('device_sensor_accelerometer_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Configure compression for device_health_heartrate_raw (60 days retention)
ALTER TABLE device_health_heartrate_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('device_health_heartrate_raw', INTERVAL '14 days', if_not_exists => TRUE);

-- Configure compression for device_state_power_raw (30 days retention)
ALTER TABLE device_state_power_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('device_state_power_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Configure compression for device_system_apps_macos_raw (30 days retention)
ALTER TABLE device_system_apps_macos_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id,app_bundle_id'
);
SELECT add_compression_policy('device_system_apps_macos_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Configure compression for device_system_apps_android_raw (30 days retention)
ALTER TABLE device_system_apps_android_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id,package_name'
);
SELECT add_compression_policy('device_system_apps_android_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Configure compression for device_metadata_raw (90 days retention)
ALTER TABLE device_metadata_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id,key'
);
SELECT add_compression_policy('device_metadata_raw', INTERVAL '30 days', if_not_exists => TRUE);
