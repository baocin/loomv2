-- Migration 022: Add trace_id columns for unified data mapping
-- Description: Adds trace_id columns to existing tables to enable upsert-based data mapping

-- Add trace_id to external data tables
ALTER TABLE external_email_events_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE external_calendar_events_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE external_twitter_liked_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE digital_clipboard_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE digital_web_analytics_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE device_network_wifi_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE device_network_bluetooth_raw
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE task_url_ingest
ADD COLUMN IF NOT EXISTS trace_id TEXT;

-- Add trace_id to device sensor tables (these need to be created first)
CREATE TABLE IF NOT EXISTS device_sensor_gps_raw (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    altitude REAL,
    accuracy REAL,
    speed REAL,
    heading REAL,
    provider TEXT,
    activity TEXT,
    battery_level INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (trace_id, timestamp)
);

CREATE TABLE IF NOT EXISTS device_sensor_accelerometer_raw (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    x_axis REAL NOT NULL,
    y_axis REAL NOT NULL,
    z_axis REAL NOT NULL,
    magnitude REAL,
    sample_rate INTEGER,
    activity TEXT,
    device_orientation TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (trace_id, timestamp)
);

CREATE TABLE IF NOT EXISTS device_health_heartrate_raw (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    heart_rate INTEGER NOT NULL,
    confidence REAL,
    measurement_type TEXT,
    variability INTEGER,
    activity TEXT,
    device_model TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (trace_id, timestamp)
);

CREATE TABLE IF NOT EXISTS device_state_power_raw (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    battery_level INTEGER NOT NULL,
    is_charging BOOLEAN NOT NULL DEFAULT FALSE,
    power_source TEXT,
    battery_health INTEGER,
    temperature_celsius REAL,
    cycles INTEGER,
    time_to_full INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (trace_id, timestamp)
);

CREATE TABLE IF NOT EXISTS external_twitter_images_raw (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    tweet_id TEXT NOT NULL,
    tweet_url TEXT,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    image_data BYTEA,
    format TEXT,
    width INTEGER,
    height INTEGER,
    screenshot_timestamp TIMESTAMPTZ,
    processor_version TEXT,
    screenshot_tool TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (trace_id, timestamp),
    UNIQUE (tweet_id, timestamp)
);

-- Convert new tables to hypertables
SELECT create_hypertable('device_sensor_gps_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_sensor_accelerometer_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_health_heartrate_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_state_power_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_twitter_images_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for trace_id on existing tables
CREATE INDEX IF NOT EXISTS idx_email_trace_id ON external_email_events_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_calendar_trace_id ON external_calendar_events_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_twitter_liked_trace_id ON external_twitter_liked_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_clipboard_trace_id ON digital_clipboard_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_web_analytics_trace_id ON digital_web_analytics_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_wifi_trace_id ON device_network_wifi_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_bluetooth_trace_id ON device_network_bluetooth_raw (trace_id);
CREATE INDEX IF NOT EXISTS idx_url_ingest_trace_id ON task_url_ingest (trace_id);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_gps_trace_id ON device_sensor_gps_raw (trace_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_device_time ON device_sensor_gps_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_gps_location ON device_sensor_gps_raw (latitude, longitude);

CREATE INDEX IF NOT EXISTS idx_accelerometer_trace_id ON device_sensor_accelerometer_raw (trace_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_accelerometer_device_time ON device_sensor_accelerometer_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_accelerometer_activity ON device_sensor_accelerometer_raw (activity, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_heartrate_trace_id ON device_health_heartrate_raw (trace_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_heartrate_device_time ON device_health_heartrate_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_heartrate_value ON device_health_heartrate_raw (heart_rate, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_power_trace_id ON device_state_power_raw (trace_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_power_device_time ON device_state_power_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_power_battery ON device_state_power_raw (battery_level, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_twitter_images_trace_id ON external_twitter_images_raw (trace_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_images_tweet_id ON external_twitter_images_raw (tweet_id);
CREATE INDEX IF NOT EXISTS idx_twitter_images_device_time ON external_twitter_images_raw (device_id, timestamp DESC);

-- Configure compression for new tables
ALTER TABLE device_sensor_gps_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

ALTER TABLE device_sensor_accelerometer_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

ALTER TABLE device_health_heartrate_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

ALTER TABLE device_state_power_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

ALTER TABLE external_twitter_images_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

-- Add compression policies
SELECT add_compression_policy('device_sensor_gps_raw', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('device_sensor_accelerometer_raw', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('device_health_heartrate_raw', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('device_state_power_raw', INTERVAL '1 day', if_not_exists => TRUE);
SELECT add_compression_policy('external_twitter_images_raw', INTERVAL '7 days', if_not_exists => TRUE);

-- Add retention policies
SELECT add_retention_policy('device_sensor_gps_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_sensor_accelerometer_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_health_heartrate_raw', INTERVAL '60 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_state_power_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('external_twitter_images_raw', INTERVAL '90 days', if_not_exists => TRUE);

-- Update existing twitter_extraction_results to have trace_id if not exists
ALTER TABLE twitter_extraction_results
ADD COLUMN IF NOT EXISTS trace_id TEXT;

CREATE INDEX IF NOT EXISTS idx_twitter_extraction_trace_id ON twitter_extraction_results (trace_id);

-- Update existing embedding tables to have trace_id if not exists
ALTER TABLE emails_with_embeddings
ADD COLUMN IF NOT EXISTS trace_id TEXT;

ALTER TABLE twitter_likes_with_embeddings
ADD COLUMN IF NOT EXISTS trace_id TEXT;

CREATE INDEX IF NOT EXISTS idx_emails_embeddings_trace_id ON emails_with_embeddings (trace_id);
CREATE INDEX IF NOT EXISTS idx_twitter_embeddings_trace_id ON twitter_likes_with_embeddings (trace_id);
