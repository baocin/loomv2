-- Migration 044: Create Individual App Usage Tables
-- Description: Creates tables for individual Android app events and category aggregations

-- Individual Android App Events Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_events_individual (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    message_id TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    package_name TEXT NOT NULL,
    app_name TEXT,
    event_type TEXT NOT NULL,
    class_name TEXT,
    configuration JSONB DEFAULT '{}',
    shortcut_id TEXT,
    standby_bucket INT,
    notification_channel_id TEXT,
    metadata JSONB DEFAULT '{}',
    trace_id TEXT,
    services_encountered TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, message_id)
);

-- Android App Categories Aggregated Table (main table for category stats)
CREATE TABLE IF NOT EXISTS device_app_usage_android_categories_aggregated (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    message_id TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    aggregation_period_end TIMESTAMPTZ NOT NULL,
    total_screen_time_ms BIGINT NOT NULL,
    device_unlocks INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    trace_id TEXT,
    services_encountered TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start)
);

-- Android App Categories Detail Table (child table for category breakdown)
CREATE TABLE IF NOT EXISTS device_app_usage_android_categories_detail (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    category TEXT NOT NULL,
    total_time_ms BIGINT NOT NULL,
    app_count INT NOT NULL,
    percentage_of_total REAL NOT NULL CHECK (percentage_of_total >= 0 AND percentage_of_total <= 100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start, category),
    FOREIGN KEY (device_id, aggregation_period_start)
        REFERENCES device_app_usage_android_categories_aggregated(device_id, aggregation_period_start) ON DELETE CASCADE
);

-- Convert tables to hypertables
SELECT create_hypertable('device_app_usage_android_events_individual', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_app_usage_android_categories_aggregated', 'aggregation_period_start', if_not_exists => TRUE);

-- Create indexes for individual events table
CREATE INDEX IF NOT EXISTS idx_app_events_individual_device_time
    ON device_app_usage_android_events_individual (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_app_events_individual_package
    ON device_app_usage_android_events_individual (package_name);
CREATE INDEX IF NOT EXISTS idx_app_events_individual_event_type
    ON device_app_usage_android_events_individual (event_type);
CREATE INDEX IF NOT EXISTS idx_app_events_individual_message_id
    ON device_app_usage_android_events_individual (message_id);
CREATE INDEX IF NOT EXISTS idx_app_events_individual_trace_id
    ON device_app_usage_android_events_individual (trace_id) WHERE trace_id IS NOT NULL;

-- Create indexes for category aggregated table
CREATE INDEX IF NOT EXISTS idx_app_categories_aggregated_device_time
    ON device_app_usage_android_categories_aggregated (device_id, aggregation_period_start DESC);
CREATE INDEX IF NOT EXISTS idx_app_categories_aggregated_message_id
    ON device_app_usage_android_categories_aggregated (message_id);
CREATE INDEX IF NOT EXISTS idx_app_categories_aggregated_trace_id
    ON device_app_usage_android_categories_aggregated (trace_id) WHERE trace_id IS NOT NULL;

-- Create indexes for category detail table
CREATE INDEX IF NOT EXISTS idx_app_categories_detail_device_category
    ON device_app_usage_android_categories_detail (device_id, category);
CREATE INDEX IF NOT EXISTS idx_app_categories_detail_category
    ON device_app_usage_android_categories_detail (category);

-- Set compression policy for hypertables (compress data older than 7 days)
SELECT add_compression_policy('device_app_usage_android_events_individual', INTERVAL '7 days');
SELECT add_compression_policy('device_app_usage_android_categories_aggregated', INTERVAL '7 days');

-- Set retention policy (keep individual events for 30 days, categories for 90 days)
SELECT add_retention_policy('device_app_usage_android_events_individual', INTERVAL '30 days');
SELECT add_retention_policy('device_app_usage_android_categories_aggregated', INTERVAL '90 days');
