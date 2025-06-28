-- Migration 023: Standardize trace_id across all tables and unify Twitter data
-- Description: Adds trace_id with unique constraints to all tables and merges Twitter tables into twitter_posts

-- First, create the unified twitter_posts table
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

    PRIMARY KEY (tweet_id),
    UNIQUE (trace_id)
);

-- Convert to hypertable
SELECT create_hypertable('twitter_posts', 'timestamp', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_twitter_posts_trace_id ON twitter_posts (trace_id);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_tweet_id ON twitter_posts (tweet_id);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_device_time ON twitter_posts (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_author ON twitter_posts (author_username, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_created_at ON twitter_posts (created_at_twitter DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_liked_at ON twitter_posts (liked_at DESC);
CREATE INDEX IF NOT EXISTS idx_twitter_posts_has_media ON twitter_posts (has_media) WHERE has_media = TRUE;
CREATE INDEX IF NOT EXISTS idx_twitter_posts_embedding ON twitter_posts USING gin(embedding) WHERE embedding IS NOT NULL;

-- Migrate data from existing tables
-- From external_twitter_liked_raw
INSERT INTO twitter_posts (
    trace_id, tweet_id, tweet_url, tweet_text, author_username, author_display_name,
    created_at_twitter, liked_at, device_id, timestamp, schema_version,
    like_count, retweet_count, reply_count, is_retweet, has_media, media_urls,
    user_agent, metadata
)
SELECT
    COALESCE(trace_id, tweet_id || '-' || EXTRACT(EPOCH FROM timestamp)::TEXT),
    tweet_id, tweet_url, tweet_text, author_username, author_display_name,
    created_at_twitter, liked_at, device_id, timestamp, schema_version,
    like_count, retweet_count, reply_count, is_retweet, has_media, media_urls,
    user_agent, metadata
FROM external_twitter_liked_raw
ON CONFLICT (tweet_id) DO UPDATE SET
    tweet_text = EXCLUDED.tweet_text,
    like_count = EXCLUDED.like_count,
    retweet_count = EXCLUDED.retweet_count,
    reply_count = EXCLUDED.reply_count,
    metadata = EXCLUDED.metadata;

-- From twitter_extraction_results
UPDATE twitter_posts tp
SET
    extracted_text = ter.extracted_text,
    extracted_urls = ter.urls,
    extracted_hashtags = ter.hashtags,
    extracted_mentions = ter.mentions,
    screenshot_path = ter.screenshot_path,
    processing_time_ms = ter.processing_time_ms
FROM twitter_extraction_results ter
WHERE tp.tweet_id = ter.tweet_id;

-- From twitter_likes_with_embeddings
UPDATE twitter_posts tp
SET
    embedding = tle.embedding,
    embedding_model = tle.model,
    embedding_dimensions = tle.dimensions,
    embedding_created_at = tle.created_at
FROM twitter_likes_with_embeddings tle
WHERE tp.tweet_id = tle.tweet_id;

-- Now add trace_id to all tables that don't have it yet
-- Device tables
ALTER TABLE device_audio_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_health_blood_oxygen_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_health_blood_pressure_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_health_sleep_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_health_steps_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_image_camera_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_input_keyboard_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_input_mouse_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_input_touch_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_metadata_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_network_stats_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_sensor_barometer_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_sensor_gyroscope_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_sensor_light_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_sensor_magnetometer_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_sensor_temperature_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_system_apps_android_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_system_apps_macos_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_text_notes_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE device_video_screen_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Digital tables
ALTER TABLE digital_clipboard_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE digital_web_analytics_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- External tables
ALTER TABLE external_calendar_events_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE external_email_events_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE external_hackernews_activity_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE external_reddit_activity_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE external_twitter_liked_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE external_web_visits_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Media tables
ALTER TABLE media_audio_voice_segments_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE media_image_analysis_minicpm_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE media_image_vision_annotations_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE media_text_word_timestamps_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- OS events tables
ALTER TABLE os_events_app_lifecycle_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE os_events_notifications_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE os_events_system_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Task tables
ALTER TABLE task_url_ingest ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE task_url_processed_content_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE task_url_processed_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Analysis tables
ALTER TABLE analysis_audio_emotion_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_audio_emotion_scores_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_context_inference_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_context_reasoning_chains_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_image_emotion_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_image_face_emotions_raw ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_image_recognition_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_inferred_context_mistral_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE analysis_transcription_results ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Embedding tables
ALTER TABLE embeddings_image_nomic ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;
ALTER TABLE embeddings_text_nomic ADD COLUMN IF NOT EXISTS trace_id TEXT DEFAULT gen_random_uuid()::TEXT;

-- Now update all NULL trace_ids with generated UUIDs for existing records
UPDATE device_audio_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_health_blood_oxygen_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_health_blood_pressure_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_health_heartrate_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_health_sleep_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_health_steps_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_image_camera_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_input_keyboard_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_input_mouse_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_input_touch_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_metadata_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_network_bluetooth_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_network_stats_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_network_wifi_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_accelerometer_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_barometer_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_gps_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_gyroscope_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_light_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_magnetometer_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_sensor_temperature_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_state_power_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_system_apps_android_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_system_apps_macos_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_text_notes_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE device_video_screen_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE digital_clipboard_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE digital_web_analytics_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE external_calendar_events_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_email_events_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_hackernews_activity_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_reddit_activity_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_twitter_liked_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_twitter_images_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE external_web_visits_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE media_audio_voice_segments_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE media_image_analysis_minicpm_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE media_image_vision_annotations_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE media_text_word_timestamps_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE os_events_app_lifecycle_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE os_events_notifications_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE os_events_system_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE task_url_ingest SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE task_url_processed_content_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE task_url_processed_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE analysis_audio_emotion_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_audio_emotion_scores_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_context_inference_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_context_reasoning_chains_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_image_emotion_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_image_face_emotions_raw SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_image_recognition_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_inferred_context_mistral_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE analysis_transcription_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE embeddings_image_nomic SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE embeddings_text_nomic SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

UPDATE emails_with_embeddings SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE twitter_likes_with_embeddings SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';
UPDATE twitter_extraction_results SET trace_id = gen_random_uuid()::TEXT WHERE trace_id IS NULL OR trace_id = '';

-- Now make trace_id NOT NULL and add unique constraints
-- For hypertables, we need to include the partitioning column in the unique constraint
-- Device tables
ALTER TABLE device_audio_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_audio_trace_unique ON device_audio_raw (trace_id, timestamp);

ALTER TABLE device_health_blood_oxygen_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_health_blood_oxygen_trace_unique ON device_health_blood_oxygen_raw (trace_id, timestamp);

ALTER TABLE device_health_blood_pressure_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_health_blood_pressure_trace_unique ON device_health_blood_pressure_raw (trace_id, timestamp);

ALTER TABLE device_health_heartrate_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_health_heartrate_trace_unique ON device_health_heartrate_raw (trace_id, timestamp);

ALTER TABLE device_health_sleep_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_health_sleep_trace_unique ON device_health_sleep_raw (trace_id, timestamp);

ALTER TABLE device_health_steps_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_health_steps_trace_unique ON device_health_steps_raw (trace_id, timestamp);

ALTER TABLE device_image_camera_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_image_camera_trace_unique ON device_image_camera_raw (trace_id, timestamp);

ALTER TABLE device_input_keyboard_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_input_keyboard_trace_unique ON device_input_keyboard_raw (trace_id, timestamp);

ALTER TABLE device_input_mouse_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_input_mouse_trace_unique ON device_input_mouse_raw (trace_id, timestamp);

ALTER TABLE device_input_touch_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_input_touch_trace_unique ON device_input_touch_raw (trace_id, timestamp);

ALTER TABLE device_metadata_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_metadata_trace_unique ON device_metadata_raw (trace_id, timestamp);

ALTER TABLE device_network_bluetooth_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_network_bluetooth_trace_unique ON device_network_bluetooth_raw (trace_id, timestamp);

ALTER TABLE device_network_stats_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_network_stats_trace_unique ON device_network_stats_raw (trace_id, timestamp);

ALTER TABLE device_network_wifi_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_network_wifi_trace_unique ON device_network_wifi_raw (trace_id, timestamp);

ALTER TABLE device_sensor_accelerometer_raw ALTER COLUMN trace_id SET NOT NULL;
-- Already has unique constraint

ALTER TABLE device_sensor_barometer_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_sensor_barometer_trace_unique ON device_sensor_barometer_raw (trace_id, timestamp);

ALTER TABLE device_sensor_gps_raw ALTER COLUMN trace_id SET NOT NULL;
-- Already has unique constraint

ALTER TABLE device_sensor_gyroscope_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_sensor_gyroscope_trace_unique ON device_sensor_gyroscope_raw (trace_id, timestamp);

ALTER TABLE device_sensor_light_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_sensor_light_trace_unique ON device_sensor_light_raw (trace_id, timestamp);

ALTER TABLE device_sensor_magnetometer_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_sensor_magnetometer_trace_unique ON device_sensor_magnetometer_raw (trace_id, timestamp);

ALTER TABLE device_sensor_temperature_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_sensor_temperature_trace_unique ON device_sensor_temperature_raw (trace_id, timestamp);

ALTER TABLE device_state_power_raw ALTER COLUMN trace_id SET NOT NULL;
-- Already has trace_id

ALTER TABLE device_system_apps_android_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_system_apps_android_trace_unique ON device_system_apps_android_raw (trace_id, timestamp);

ALTER TABLE device_system_apps_macos_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_system_apps_macos_trace_unique ON device_system_apps_macos_raw (trace_id, timestamp);

ALTER TABLE device_text_notes_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_text_notes_trace_unique ON device_text_notes_raw (trace_id, timestamp);

ALTER TABLE device_video_screen_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_video_screen_trace_unique ON device_video_screen_raw (trace_id, timestamp);

-- Digital tables
ALTER TABLE digital_clipboard_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_digital_clipboard_trace_unique ON digital_clipboard_raw (trace_id, timestamp);

ALTER TABLE digital_web_analytics_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_digital_web_analytics_trace_unique ON digital_web_analytics_raw (trace_id, timestamp);

-- External tables
ALTER TABLE external_calendar_events_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_calendar_trace_unique ON external_calendar_events_raw (trace_id, timestamp);

ALTER TABLE external_email_events_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_email_trace_unique ON external_email_events_raw (trace_id, timestamp);

ALTER TABLE external_hackernews_activity_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_hackernews_trace_unique ON external_hackernews_activity_raw (trace_id, timestamp);

ALTER TABLE external_reddit_activity_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_reddit_trace_unique ON external_reddit_activity_raw (trace_id, timestamp);

ALTER TABLE external_twitter_liked_raw ALTER COLUMN trace_id SET NOT NULL;
-- This will be dropped after migration

ALTER TABLE external_web_visits_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_external_web_visits_trace_unique ON external_web_visits_raw (trace_id, timestamp);

-- Media tables
ALTER TABLE media_audio_voice_segments_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_audio_voice_trace_unique ON media_audio_voice_segments_raw (trace_id, timestamp);

ALTER TABLE media_image_analysis_minicpm_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_image_analysis_trace_unique ON media_image_analysis_minicpm_results (trace_id, timestamp);

ALTER TABLE media_image_vision_annotations_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_image_vision_trace_unique ON media_image_vision_annotations_raw (trace_id, timestamp);

ALTER TABLE media_text_word_timestamps_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_media_text_word_trace_unique ON media_text_word_timestamps_raw (trace_id, timestamp);

-- OS events tables
ALTER TABLE os_events_app_lifecycle_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_os_events_app_trace_unique ON os_events_app_lifecycle_raw (trace_id, timestamp);

ALTER TABLE os_events_notifications_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_os_events_notifications_trace_unique ON os_events_notifications_raw (trace_id, timestamp);

ALTER TABLE os_events_system_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_os_events_system_trace_unique ON os_events_system_raw (trace_id, timestamp);

-- Task tables
ALTER TABLE task_url_ingest ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_url_ingest_trace_unique ON task_url_ingest (trace_id);

ALTER TABLE task_url_processed_content_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_url_processed_content_trace_unique ON task_url_processed_content_raw (trace_id, timestamp);

ALTER TABLE task_url_processed_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_task_url_processed_results_trace_unique ON task_url_processed_results (trace_id);

-- Analysis tables (non-hypertables get simple unique constraint)
ALTER TABLE analysis_audio_emotion_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_audio_emotion_trace_unique ON analysis_audio_emotion_results (trace_id);

ALTER TABLE analysis_audio_emotion_scores_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_audio_emotion_scores_trace_unique ON analysis_audio_emotion_scores_raw (trace_id, timestamp);

ALTER TABLE analysis_context_inference_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_context_inference_trace_unique ON analysis_context_inference_results (trace_id);

ALTER TABLE analysis_context_reasoning_chains_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_context_reasoning_trace_unique ON analysis_context_reasoning_chains_raw (trace_id, timestamp);

ALTER TABLE analysis_image_emotion_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_image_emotion_trace_unique ON analysis_image_emotion_results (trace_id);

ALTER TABLE analysis_image_face_emotions_raw ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_image_face_emotions_trace_unique ON analysis_image_face_emotions_raw (trace_id, timestamp);

ALTER TABLE analysis_image_recognition_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_image_recognition_trace_unique ON analysis_image_recognition_results (trace_id);

ALTER TABLE analysis_inferred_context_mistral_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_inferred_mistral_trace_unique ON analysis_inferred_context_mistral_results (trace_id, timestamp);

ALTER TABLE analysis_transcription_results ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_transcription_trace_unique ON analysis_transcription_results (trace_id);

-- Embedding tables
ALTER TABLE embeddings_image_nomic ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_image_trace_unique ON embeddings_image_nomic (trace_id);

ALTER TABLE embeddings_text_nomic ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_embeddings_text_trace_unique ON embeddings_text_nomic (trace_id);

ALTER TABLE emails_with_embeddings ALTER COLUMN trace_id SET NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_emails_embeddings_trace_unique ON emails_with_embeddings (trace_id);

-- Configure compression for twitter_posts
ALTER TABLE twitter_posts SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);

-- Add compression and retention policies
SELECT add_compression_policy('twitter_posts', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('twitter_posts', INTERVAL '365 days', if_not_exists => TRUE);

-- Drop old Twitter tables after verification (commented out for safety)
-- DROP TABLE IF EXISTS external_twitter_images_raw CASCADE;
-- DROP TABLE IF EXISTS twitter_extraction_results CASCADE;
-- DROP TABLE IF EXISTS twitter_likes_with_embeddings CASCADE;

-- Create a view for backward compatibility
CREATE OR REPLACE VIEW external_twitter_liked_raw_v2 AS
SELECT
    trace_id, tweet_id, tweet_url, tweet_text, author_username, author_display_name,
    created_at_twitter, liked_at, device_id, timestamp, schema_version,
    like_count, retweet_count, reply_count, is_retweet, has_media, media_urls,
    user_agent, metadata, created_at
FROM twitter_posts;
