-- Migration 007: Create Scheduled Consumer Tables
-- Description: Creates TimescaleDB hypertables for external data from scheduled consumers

-- Email Events Table
CREATE TABLE IF NOT EXISTS external_email_events_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    message_id_external TEXT NOT NULL,
    thread_id TEXT,
    from_address TEXT NOT NULL,
    to_addresses TEXT[] NOT NULL,
    cc_addresses TEXT[],
    subject TEXT NOT NULL,
    body_text TEXT,
    body_html TEXT,
    attachments JSONB,
    labels TEXT[],
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    importance TEXT,
    received_date TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id_external, timestamp)
);

-- Calendar Events Table
CREATE TABLE IF NOT EXISTS external_calendar_events_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    calendar_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    all_day BOOLEAN NOT NULL DEFAULT FALSE,
    recurring_rule TEXT,
    attendees JSONB,
    organizer_email TEXT,
    status TEXT NOT NULL,
    visibility TEXT,
    reminders JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, event_id, timestamp)
);

-- Twitter Likes Table
CREATE TABLE IF NOT EXISTS external_twitter_liked_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    tweet_id TEXT NOT NULL,
    tweet_url TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_display_name TEXT NOT NULL,
    tweet_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    liked_at TIMESTAMPTZ NOT NULL,
    retweet_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    media_urls TEXT[],
    hashtags TEXT[],
    mentions TEXT[],
    PRIMARY KEY (device_id, tweet_id, timestamp)
);

-- Reddit Activity Table
CREATE TABLE IF NOT EXISTS external_reddit_activity_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    post_title TEXT NOT NULL,
    post_url TEXT NOT NULL,
    author TEXT NOT NULL,
    content TEXT,
    score INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    interacted_at TIMESTAMPTZ NOT NULL,
    interaction_type TEXT NOT NULL,
    PRIMARY KEY (device_id, post_id, timestamp)
);

-- Hacker News Activity Table
CREATE TABLE IF NOT EXISTS external_hackernews_activity_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT,
    url TEXT,
    text TEXT,
    author TEXT NOT NULL,
    score INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL,
    interacted_at TIMESTAMPTZ NOT NULL,
    interaction_type TEXT NOT NULL,
    PRIMARY KEY (device_id, item_id, timestamp)
);

-- Web Visits Table
CREATE TABLE IF NOT EXISTS external_web_visits_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    visit_time TIMESTAMPTZ NOT NULL,
    visit_duration INTEGER,
    referrer TEXT,
    browser TEXT NOT NULL,
    tab_count INTEGER,
    is_incognito BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (device_id, url, timestamp)
);

-- RSS Feed Items Table (REMOVED - see migration 016)

-- Job Status Table
CREATE TABLE IF NOT EXISTS internal_scheduled_jobs_status (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    job_type TEXT NOT NULL,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    status TEXT NOT NULL,
    error_message TEXT,
    items_processed INTEGER DEFAULT 0,
    execution_duration NUMERIC,
    PRIMARY KEY (device_id, job_id, timestamp)
);

-- Create hypertables for all external data tables
SELECT create_hypertable('external_email_events_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_calendar_events_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_twitter_liked_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_reddit_activity_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_hackernews_activity_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('external_web_visits_raw', 'timestamp', if_not_exists => TRUE);
-- RSS hypertable removed - see migration 016
SELECT create_hypertable('internal_scheduled_jobs_status', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_external_email_from_address ON external_email_events_raw (from_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_external_email_labels ON external_email_events_raw USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_external_calendar_start_time ON external_calendar_events_raw (start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_external_twitter_author ON external_twitter_liked_raw (author_username, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_external_twitter_hashtags ON external_twitter_liked_raw USING GIN (hashtags);
CREATE INDEX IF NOT EXISTS idx_external_reddit_subreddit ON external_reddit_activity_raw (subreddit, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_external_hn_author ON external_hackernews_activity_raw (author, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_external_web_domain ON external_web_visits_raw (substring(url from 'https?://([^/]+)'), timestamp DESC);
-- RSS index removed - see migration 016
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_type ON internal_scheduled_jobs_status (job_type, timestamp DESC);

-- Configure compression for external data tables
ALTER TABLE external_email_events_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE external_calendar_events_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE external_twitter_liked_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE external_reddit_activity_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE external_hackernews_activity_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE external_web_visits_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- RSS compression config removed - see migration 016

ALTER TABLE internal_scheduled_jobs_status SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policies (compress after 1 day for most, 7 days for large tables)
-- Using simpler approach to avoid duplicates
SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_email_events_raw'
) THEN add_compression_policy('external_email_events_raw', INTERVAL '7 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_calendar_events_raw'
) THEN add_compression_policy('external_calendar_events_raw', INTERVAL '30 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_twitter_liked_raw'
) THEN add_compression_policy('external_twitter_liked_raw', INTERVAL '7 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_reddit_activity_raw'
) THEN add_compression_policy('external_reddit_activity_raw', INTERVAL '7 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_hackernews_activity_raw'
) THEN add_compression_policy('external_hackernews_activity_raw', INTERVAL '7 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'external_web_visits_raw'
) THEN add_compression_policy('external_web_visits_raw', INTERVAL '1 day') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_compression'
    AND hypertable_name = 'internal_scheduled_jobs_status'
) THEN add_compression_policy('internal_scheduled_jobs_status', INTERVAL '1 day') END;

-- Add retention policies based on data importance (using simpler conditional approach)
SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_email_events_raw'
) THEN add_retention_policy('external_email_events_raw', INTERVAL '90 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_calendar_events_raw'
) THEN add_retention_policy('external_calendar_events_raw', INTERVAL '365 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_twitter_liked_raw'
) THEN add_retention_policy('external_twitter_liked_raw', INTERVAL '365 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_reddit_activity_raw'
) THEN add_retention_policy('external_reddit_activity_raw', INTERVAL '180 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_hackernews_activity_raw'
) THEN add_retention_policy('external_hackernews_activity_raw', INTERVAL '180 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'external_web_visits_raw'
) THEN add_retention_policy('external_web_visits_raw', INTERVAL '30 days') END;

SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention'
    AND hypertable_name = 'internal_scheduled_jobs_status'
) THEN add_retention_policy('internal_scheduled_jobs_status', INTERVAL '7 days') END;

-- Show compression and retention policies
SELECT
    hypertable_name,
    compression_enabled,
    (SELECT config->>'compress_after' FROM timescaledb_information.jobs
     WHERE hypertable_name = h.hypertable_name AND proc_name = 'policy_compression' LIMIT 1) as compress_after,
    (SELECT config->>'drop_after' FROM timescaledb_information.jobs
     WHERE hypertable_name = h.hypertable_name AND proc_name = 'policy_retention' LIMIT 1) as retention_period
FROM timescaledb_information.hypertables h
WHERE hypertable_name LIKE 'external_%' OR hypertable_name LIKE 'internal_%'
ORDER BY hypertable_name;
