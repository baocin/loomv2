-- Migration 006: Create External Data Source Tables
-- Description: Creates tables for data from external sources (email, calendar, social media, etc.)

-- Email Events Table
CREATE TABLE IF NOT EXISTS external_email_events_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    thread_id TEXT,
    from_address TEXT NOT NULL,
    to_addresses TEXT[] NOT NULL,
    cc_addresses TEXT[],
    subject TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT,
    attachments JSONB, -- [{"filename": "doc.pdf", "size": 1024, "url": "s3://..."}]
    labels TEXT[],
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    importance TEXT, -- 'high', 'normal', 'low'
    received_date TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, timestamp)
);

-- Calendar Events Table
CREATE TABLE IF NOT EXISTS external_calendar_events_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    event_id TEXT NOT NULL,
    calendar_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN NOT NULL DEFAULT FALSE,
    recurring_rule TEXT, -- iCal RRULE format
    attendees JSONB, -- [{"email": "...", "name": "...", "status": "accepted"}]
    organizer_email TEXT,
    status TEXT NOT NULL, -- 'confirmed', 'tentative', 'cancelled'
    visibility TEXT, -- 'public', 'private'
    reminders JSONB, -- [{"method": "email", "minutes": 10}]
    conference_data JSONB, -- {"url": "...", "type": "zoom"}
    color_id TEXT,
    last_modified TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, event_id, timestamp)
);

-- Social Media Posts Table (Twitter/X)
CREATE TABLE IF NOT EXISTS external_twitter_liked_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    tweet_id TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_display_name TEXT,
    tweet_text TEXT NOT NULL,
    tweet_html TEXT,
    media_urls TEXT[],
    hashtags TEXT[],
    mentions TEXT[],
    urls TEXT[],
    reply_to_id TEXT,
    quote_tweet_id TEXT,
    retweet_count INT,
    like_count INT,
    reply_count INT,
    created_at_twitter TIMESTAMPTZ NOT NULL,
    liked_at TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, tweet_id, timestamp)
);

-- Clipboard History Table
CREATE TABLE IF NOT EXISTS digital_clipboard_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    content_type TEXT NOT NULL, -- 'text', 'image', 'file', 'url'
    content_text TEXT,
    content_image_url TEXT,
    content_files JSONB, -- [{"path": "...", "name": "...", "size": ...}]
    source_app TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Web Analytics Events Table
CREATE TABLE IF NOT EXISTS digital_web_analytics_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    url TEXT NOT NULL,
    title TEXT,
    domain TEXT NOT NULL,
    path TEXT NOT NULL,
    referrer TEXT,
    duration_seconds INT,
    scroll_depth_percent INT,
    interaction_count INT,
    browser_name TEXT,
    browser_version TEXT,
    tab_id TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, tab_id, timestamp)
);

-- Network Events Table
CREATE TABLE IF NOT EXISTS device_network_wifi_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    ssid TEXT,
    bssid TEXT,
    signal_strength INT, -- dBm
    frequency INT, -- MHz
    channel INT,
    security_type TEXT,
    is_connected BOOLEAN NOT NULL,
    ip_address TEXT,
    link_speed INT, -- Mbps
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Bluetooth Devices Table
CREATE TABLE IF NOT EXISTS device_network_bluetooth_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    bluetooth_address TEXT NOT NULL,
    device_name TEXT,
    device_type TEXT,
    rssi INT, -- Signal strength
    is_connected BOOLEAN NOT NULL,
    is_paired BOOLEAN NOT NULL,
    services TEXT[],
    manufacturer_data JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, bluetooth_address, timestamp)
);

-- Task URL Ingestion Queue
CREATE TABLE IF NOT EXISTS task_url_ingest (
    id BIGSERIAL,
    url TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_type TEXT NOT NULL, -- 'manual', 'scraper', 'integration'
    priority INT NOT NULL DEFAULT 5, -- 1-10, higher is more important
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (url, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('external_email_events_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_calendar_events_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_twitter_liked_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('digital_clipboard_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('digital_web_analytics_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_network_wifi_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_network_bluetooth_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('task_url_ingest', 'timestamp', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_email_device_time ON external_email_events_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_email_from ON external_email_events_raw (from_address);
CREATE INDEX IF NOT EXISTS idx_email_subject ON external_email_events_raw USING GIN (to_tsvector('english', subject));
CREATE INDEX IF NOT EXISTS idx_calendar_device_time ON external_calendar_events_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_calendar_start_time ON external_calendar_events_raw (start_time);
CREATE INDEX IF NOT EXISTS idx_twitter_device_time ON external_twitter_liked_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_text ON external_twitter_liked_raw USING GIN (to_tsvector('english', tweet_text));
CREATE INDEX IF NOT EXISTS idx_clipboard_device_time ON digital_clipboard_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_web_device_time ON digital_web_analytics_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_web_domain ON digital_web_analytics_raw (domain);
CREATE INDEX IF NOT EXISTS idx_wifi_device_time ON device_network_wifi_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bluetooth_device_time ON device_network_bluetooth_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_task_url_status ON task_url_ingest (status, priority DESC);

-- Configure compression
ALTER TABLE external_email_events_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('external_email_events_raw', INTERVAL '30 days', if_not_exists => TRUE);

ALTER TABLE external_calendar_events_raw SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('external_calendar_events_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- Add retention policies
SELECT add_retention_policy('external_email_events_raw', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('external_calendar_events_raw', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('external_twitter_liked_raw', INTERVAL '365 days', if_not_exists => TRUE);
SELECT add_retention_policy('digital_clipboard_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('digital_web_analytics_raw', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_network_wifi_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('device_network_bluetooth_raw', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('task_url_ingest', INTERVAL '7 days', if_not_exists => TRUE);
