-- Migration 013: Create OS Event Tables
-- Description: Creates tables for operating system events

-- OS App Lifecycle Events Table
CREATE TABLE IF NOT EXISTS os_events_app_lifecycle_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    app_identifier TEXT NOT NULL,
    app_name TEXT,
    event_type TEXT NOT NULL CHECK (event_type IN ('launch', 'foreground', 'background', 'terminate', 'crash')),
    duration_seconds INT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, app_identifier)
);

-- OS Notifications Table
CREATE TABLE IF NOT EXISTS os_events_notifications_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    notification_id TEXT NOT NULL,
    app_identifier TEXT NOT NULL,
    title TEXT,
    body TEXT,
    action TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, notification_id)
);

-- OS System Events Table
CREATE TABLE IF NOT EXISTS os_events_system_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    event_type TEXT NOT NULL,
    event_category TEXT,
    severity TEXT,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('os_events_app_lifecycle_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('os_events_notifications_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('os_events_system_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_app_lifecycle_device_time ON os_events_app_lifecycle_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_device_time ON os_events_notifications_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_device_time ON os_events_system_raw (device_id, timestamp DESC);