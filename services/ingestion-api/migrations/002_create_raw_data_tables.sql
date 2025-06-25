-- Migration 002: Create Raw Data Tables
-- Description: Creates hypertables for all raw data ingestion topics

-- Device Audio Table
CREATE TABLE IF NOT EXISTS device_audio_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    chunk_number INT NOT NULL,
    audio_data TEXT NOT NULL, -- Base64 encoded audio
    format TEXT NOT NULL,
    sample_rate INT NOT NULL,
    channels INT NOT NULL,
    duration_ms INT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, chunk_number)
);

-- Device Sensor GPS Table
CREATE TABLE IF NOT EXISTS device_sensor_gps_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    altitude DOUBLE PRECISION,
    accuracy DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    bearing DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Sensor Accelerometer Table
CREATE TABLE IF NOT EXISTS device_sensor_accelerometer_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL DEFAULT 'm/s²',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Health Heartrate Table
CREATE TABLE IF NOT EXISTS device_health_heartrate_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    heart_rate INT NOT NULL,
    confidence DOUBLE PRECISION,
    measurement_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device State Power Table
CREATE TABLE IF NOT EXISTS device_state_power_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    battery_level INT NOT NULL CHECK (battery_level >= 0 AND battery_level <= 100),
    is_charging BOOLEAN NOT NULL,
    is_plugged_in BOOLEAN NOT NULL,
    battery_temperature DOUBLE PRECISION,
    voltage DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device System Apps macOS Table
CREATE TABLE IF NOT EXISTS device_system_apps_macos_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    app_bundle_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT,
    is_active BOOLEAN NOT NULL,
    duration_seconds INT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, app_bundle_id)
);

-- Device System Apps Android Table
CREATE TABLE IF NOT EXISTS device_system_apps_android_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    package_name TEXT NOT NULL,
    app_name TEXT NOT NULL,
    activity_name TEXT,
    is_foreground BOOLEAN NOT NULL,
    duration_seconds INT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, package_name)
);

-- Device Metadata Table
CREATE TABLE IF NOT EXISTS device_metadata_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    category TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, key)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_audio_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_gps_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_accelerometer_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_heartrate_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_state_power_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_system_apps_macos_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_system_apps_android_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_metadata_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_audio_device_time ON device_audio_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_device_time ON device_sensor_gps_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_accel_device_time ON device_sensor_accelerometer_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_heartrate_device_time ON device_health_heartrate_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_power_device_time ON device_state_power_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_macos_apps_device_time ON device_system_apps_macos_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_android_apps_device_time ON device_system_apps_android_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metadata_device_time ON device_metadata_raw (device_id, timestamp DESC);
