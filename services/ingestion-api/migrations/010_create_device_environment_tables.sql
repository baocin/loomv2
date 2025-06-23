-- Migration 010: Create Device Environment Tables
-- Description: Creates tables for environmental sensor data

-- Device Temperature Table
CREATE TABLE IF NOT EXISTS device_sensor_temperature_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    temperature DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL DEFAULT 'celsius',
    sensor_location TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Barometer Table
CREATE TABLE IF NOT EXISTS device_sensor_barometer_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    pressure DOUBLE PRECISION NOT NULL,
    altitude DOUBLE PRECISION,
    unit TEXT NOT NULL DEFAULT 'hPa',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Light Sensor Table
CREATE TABLE IF NOT EXISTS device_sensor_light_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    lux DOUBLE PRECISION NOT NULL,
    color_temperature INT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Gyroscope Table
CREATE TABLE IF NOT EXISTS device_sensor_gyroscope_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL DEFAULT 'rad/s',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Magnetometer Table
CREATE TABLE IF NOT EXISTS device_sensor_magnetometer_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL DEFAULT 'μT',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_sensor_temperature_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_barometer_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_light_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_gyroscope_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_magnetometer_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_temperature_device_time ON device_sensor_temperature_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_barometer_device_time ON device_sensor_barometer_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_light_device_time ON device_sensor_light_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gyroscope_device_time ON device_sensor_gyroscope_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_magnetometer_device_time ON device_sensor_magnetometer_raw (device_id, timestamp DESC);