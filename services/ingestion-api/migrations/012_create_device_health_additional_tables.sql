-- Migration 012: Create Additional Device Health Tables
-- Description: Creates additional health monitoring tables

-- Device Health Steps Table
CREATE TABLE IF NOT EXISTS device_health_steps_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    step_count INT NOT NULL,
    distance_meters DOUBLE PRECISION,
    calories_burned DOUBLE PRECISION,
    activity_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Health Sleep Table
CREATE TABLE IF NOT EXISTS device_health_sleep_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    sleep_stage TEXT NOT NULL CHECK (sleep_stage IN ('awake', 'light', 'deep', 'rem')),
    duration_seconds INT NOT NULL,
    quality_score DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Health Blood Oxygen Table
CREATE TABLE IF NOT EXISTS device_health_blood_oxygen_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    spo2_percentage INT NOT NULL CHECK (spo2_percentage >= 0 AND spo2_percentage <= 100),
    confidence DOUBLE PRECISION,
    measurement_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Health Blood Pressure Table
CREATE TABLE IF NOT EXISTS device_health_blood_pressure_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    systolic INT NOT NULL,
    diastolic INT NOT NULL,
    pulse INT,
    measurement_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_health_steps_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_sleep_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_blood_oxygen_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_blood_pressure_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_steps_device_time ON device_health_steps_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sleep_device_time ON device_health_sleep_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_blood_oxygen_device_time ON device_health_blood_oxygen_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_blood_pressure_device_time ON device_health_blood_pressure_raw (device_id, timestamp DESC);