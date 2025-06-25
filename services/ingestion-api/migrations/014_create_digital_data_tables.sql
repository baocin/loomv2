-- Migration 014: Create Digital Data Tables
-- Description: Creates tables for digital data (clipboard, web analytics)

-- Digital Clipboard Table
CREATE TABLE IF NOT EXISTS digital_clipboard_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    content_type TEXT NOT NULL CHECK (content_type IN ('text', 'image', 'file', 'url', 'mixed')),
    content_text TEXT,
    content_data TEXT, -- Base64 for non-text content
    source_app TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Digital Web Analytics Table
CREATE TABLE IF NOT EXISTS digital_web_analytics_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    url TEXT NOT NULL,
    page_title TEXT,
    domain TEXT NOT NULL,
    time_spent_seconds INT,
    scroll_depth_percentage INT,
    clicks_count INT,
    referrer TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, url)
);

-- Convert tables to hypertables
SELECT create_hypertable('digital_clipboard_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('digital_web_analytics_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_clipboard_device_time ON digital_clipboard_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_web_analytics_device_time ON digital_web_analytics_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_web_analytics_domain ON digital_web_analytics_raw (domain, timestamp DESC);
