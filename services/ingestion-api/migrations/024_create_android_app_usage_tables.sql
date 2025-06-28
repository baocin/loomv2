-- Migration 024: Create Android App Usage Tables
-- Description: Creates tables for pre-aggregated Android app usage statistics

-- Android App Usage Aggregated Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_aggregated (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    message_id TEXT NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    aggregation_period_end TIMESTAMPTZ NOT NULL,
    aggregation_interval_minutes INT NOT NULL DEFAULT 60,
    total_screen_time_ms BIGINT NOT NULL,
    total_unlocks INT DEFAULT 0,
    trace_id TEXT,
    services_encountered TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start)
);

-- Android App Usage Stats Detail Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_stats (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    package_name TEXT NOT NULL,
    app_name TEXT,
    total_time_foreground_ms BIGINT NOT NULL,
    last_time_used TIMESTAMPTZ NOT NULL,
    last_time_foreground_service_used TIMESTAMPTZ,
    total_time_foreground_service_used_ms BIGINT DEFAULT 0,
    launch_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start, package_name),
    FOREIGN KEY (device_id, aggregation_period_start)
        REFERENCES device_app_usage_android_aggregated(device_id, aggregation_period_start) ON DELETE CASCADE
);

-- Android App Event Stats Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_events (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    package_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_count INT NOT NULL,
    last_event_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start, package_name, event_type),
    FOREIGN KEY (device_id, aggregation_period_start)
        REFERENCES device_app_usage_android_aggregated(device_id, aggregation_period_start) ON DELETE CASCADE
);

-- Android Screen Time by Category Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_categories (
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
        REFERENCES device_app_usage_android_aggregated(device_id, aggregation_period_start) ON DELETE CASCADE
);

-- Android Notification Stats Table
CREATE TABLE IF NOT EXISTS device_app_usage_android_notifications (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    aggregation_period_start TIMESTAMPTZ NOT NULL,
    package_name TEXT NOT NULL,
    notification_count INT NOT NULL,
    interaction_count INT DEFAULT 0,
    dismissal_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, aggregation_period_start, package_name),
    FOREIGN KEY (device_id, aggregation_period_start)
        REFERENCES device_app_usage_android_aggregated(device_id, aggregation_period_start) ON DELETE CASCADE
);

-- Convert main table to hypertable
SELECT create_hypertable('device_app_usage_android_aggregated', 'aggregation_period_start', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_app_usage_aggregated_device_time
    ON device_app_usage_android_aggregated (device_id, aggregation_period_start DESC);
CREATE INDEX IF NOT EXISTS idx_app_usage_aggregated_message_id
    ON device_app_usage_android_aggregated (message_id);
CREATE INDEX IF NOT EXISTS idx_app_usage_aggregated_trace_id
    ON device_app_usage_android_aggregated (trace_id) WHERE trace_id IS NOT NULL;

-- Indexes for detail tables
CREATE INDEX IF NOT EXISTS idx_app_usage_stats_device_package
    ON device_app_usage_android_stats (device_id, package_name);
CREATE INDEX IF NOT EXISTS idx_app_usage_stats_last_used
    ON device_app_usage_android_stats (last_time_used DESC);

CREATE INDEX IF NOT EXISTS idx_app_usage_events_device_package
    ON device_app_usage_android_events (device_id, package_name);
CREATE INDEX IF NOT EXISTS idx_app_usage_events_type
    ON device_app_usage_android_events (event_type);

CREATE INDEX IF NOT EXISTS idx_app_usage_categories_device
    ON device_app_usage_android_categories (device_id, category);

CREATE INDEX IF NOT EXISTS idx_app_usage_notifications_device_package
    ON device_app_usage_android_notifications (device_id, package_name);

-- Set compression policy for the hypertable (compress data older than 7 days)
SELECT add_compression_policy('device_app_usage_android_aggregated', INTERVAL '7 days');

-- Set retention policy (keep data for 90 days)
SELECT add_retention_policy('device_app_usage_android_aggregated', INTERVAL '90 days');
