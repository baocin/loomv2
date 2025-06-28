-- Migration 023: Add trace_id to tables that are missing it
-- For hypertables, we'll use empty string default and update later

-- First, let's check which tables exist and add trace_id where needed
DO $$
DECLARE
    table_record RECORD;
    has_trace_id BOOLEAN;
BEGIN
    -- List of tables that should have trace_id
    FOR table_record IN
        SELECT table_name::text
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        AND table_name LIKE '%_raw' OR table_name LIKE '%_results' OR table_name LIKE '%_embeddings'
    LOOP
        -- Check if trace_id already exists
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = table_record.table_name
            AND column_name = 'trace_id'
        ) INTO has_trace_id;

        -- Add trace_id if it doesn't exist
        IF NOT has_trace_id THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN trace_id TEXT DEFAULT ''''', table_record.table_name);
            RAISE NOTICE 'Added trace_id to %', table_record.table_name;
        END IF;
    END LOOP;
END $$;

-- Update empty trace_ids with UUIDs
UPDATE device_audio_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_image_camera_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_video_screen_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_metadata_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_network_bluetooth_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_network_wifi_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_system_apps_android_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE device_system_apps_macos_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE digital_clipboard_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE digital_web_analytics_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE external_calendar_events_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE external_email_events_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE external_twitter_liked_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;
UPDATE task_url_ingest SET trace_id = gen_random_uuid()::TEXT WHERE trace_id = '' OR trace_id IS NULL;

-- Create unified twitter_posts table
CREATE TABLE IF NOT EXISTS twitter_posts (
    id BIGSERIAL,
    trace_id TEXT NOT NULL,
    tweet_id TEXT NOT NULL,
    tweet_url TEXT,
    tweet_text TEXT,
    author_username TEXT,
    author_display_name TEXT,
    created_at_twitter TIMESTAMPTZ,
    liked_at TIMESTAMPTZ,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',

    -- Metrics
    like_count INTEGER,
    retweet_count INTEGER,
    reply_count INTEGER,
    view_count INTEGER,

    -- Flags
    is_retweet BOOLEAN DEFAULT FALSE,
    has_media BOOLEAN DEFAULT FALSE,
    is_reply BOOLEAN DEFAULT FALSE,
    is_quote BOOLEAN DEFAULT FALSE,

    -- Media and content
    media_urls TEXT[],
    screenshot_path TEXT,
    screenshot_timestamp TIMESTAMPTZ,

    -- Extracted/processed content
    extracted_text TEXT,
    extracted_urls TEXT[],
    extracted_hashtags TEXT[],
    extracted_mentions TEXT[],

    -- Embeddings
    embedding REAL[],
    embedding_model TEXT,
    embedding_dimensions INTEGER,
    embedding_created_at TIMESTAMPTZ,

    -- Metadata
    user_agent TEXT,
    processor_version TEXT,
    processing_time_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (tweet_id, timestamp)
);

-- Convert to hypertable if not already
SELECT create_hypertable('twitter_posts', 'timestamp', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_twitter_posts_trace_id ON twitter_posts (trace_id);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_tweet_id ON twitter_posts (tweet_id);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_device_time ON twitter_posts (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_author ON twitter_posts (author_username, timestamp DESC);

-- For hypertables, create composite unique indexes including timestamp
-- GPS already has one, add for others
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_audio_trace_time ON device_audio_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_image_trace_time ON device_image_camera_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_video_trace_time ON device_video_screen_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_metadata_trace_time ON device_metadata_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_network_bt_trace_time ON device_network_bluetooth_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_network_wifi_trace_time ON device_network_wifi_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_apps_android_trace_time ON device_system_apps_android_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_apps_macos_trace_time ON device_system_apps_macos_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_digital_clipboard_trace_time ON digital_clipboard_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_digital_web_trace_time ON digital_web_analytics_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_calendar_trace_time ON external_calendar_events_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_email_trace_time ON external_email_events_raw (trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_twitter_trace_time ON external_twitter_liked_raw (trace_id, timestamp);

-- For non-hypertables, create simple unique constraint
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_url_ingest_trace ON task_url_ingest (trace_id);

-- Migrate Twitter data if tables exist
INSERT INTO twitter_posts (
    trace_id, tweet_id, tweet_url, tweet_text, author_username, author_display_name,
    created_at_twitter, liked_at, device_id, timestamp, schema_version,
    like_count, retweet_count, reply_count, is_retweet, has_media, media_urls,
    user_agent, metadata
)
SELECT DISTINCT ON (tweet_id)
    COALESCE(trace_id, tweet_id || '-' || EXTRACT(EPOCH FROM timestamp)::TEXT),
    tweet_id, tweet_url, tweet_text, author_username, author_display_name,
    created_at_twitter, liked_at, device_id, timestamp, schema_version,
    like_count, retweet_count, reply_count, is_retweet, has_media, media_urls,
    user_agent, metadata
FROM external_twitter_liked_raw
WHERE tweet_id IS NOT NULL
ON CONFLICT (tweet_id, timestamp) DO NOTHING;

-- Update with extraction results if the table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'twitter_extraction_results') THEN
        UPDATE twitter_posts tp
        SET
            extracted_text = ter.extracted_text,
            screenshot_path = ter.screenshot_path,
            processing_time_ms = ter.processing_time_ms
        FROM twitter_extraction_results ter
        WHERE tp.tweet_id = ter.tweet_id;
    END IF;
END $$;

-- Update with embeddings if the table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'twitter_likes_with_embeddings') THEN
        UPDATE twitter_posts tp
        SET
            embedding = tle.embedding,
            embedding_created_at = tle.created_at
        FROM twitter_likes_with_embeddings tle
        WHERE tp.tweet_id = tle.tweet_id;
    END IF;
END $$;
