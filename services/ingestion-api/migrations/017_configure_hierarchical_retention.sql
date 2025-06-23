-- Migration 017: Configure Hierarchical Data Retention
-- Description: Implements tiered data retention with automatic downsampling

-- Create continuous aggregates for downsampled data
-- Voice segments: Full data for 7 days, then 1-minute aggregates for 30 days, then 1-hour aggregates for 365 days
CREATE MATERIALIZED VIEW IF NOT EXISTS media_audio_voice_segments_1min
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 minute', timestamp) AS bucket,
    COUNT(*) as segment_count,
    AVG(confidence_score) as avg_confidence,
    MIN(timestamp) as first_segment,
    MAX(timestamp) as last_segment
FROM media_audio_voice_segments_raw
GROUP BY device_id, bucket;

CREATE MATERIALIZED VIEW IF NOT EXISTS media_audio_voice_segments_1hour
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 hour', bucket) AS bucket,
    SUM(segment_count) as total_segments,
    AVG(avg_confidence) as avg_confidence,
    MIN(first_segment) as first_segment,
    MAX(last_segment) as last_segment
FROM media_audio_voice_segments_1min
GROUP BY device_id, bucket;

-- Word timestamps: Full data for 15 days, then 5-minute aggregates for 90 days, then 1-hour aggregates for 365 days
CREATE MATERIALIZED VIEW IF NOT EXISTS media_text_word_timestamps_5min
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('5 minutes', timestamp) AS bucket,
    COUNT(*) as word_count,
    string_agg(DISTINCT speaker_id, ',') as speakers,
    AVG(confidence_score) as avg_confidence,
    MIN(timestamp) as first_word,
    MAX(timestamp) as last_word
FROM media_text_word_timestamps_raw
GROUP BY device_id, bucket;

CREATE MATERIALIZED VIEW IF NOT EXISTS media_text_word_timestamps_1hour
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 hour', bucket) AS bucket,
    SUM(word_count) as total_words,
    string_agg(DISTINCT speakers, ',') as all_speakers,
    AVG(avg_confidence) as avg_confidence,
    MIN(first_word) as first_word,
    MAX(last_word) as last_word
FROM media_text_word_timestamps_5min
GROUP BY device_id, bucket;

-- Vision annotations: Full data for 15 days, then 10-minute aggregates for 90 days, then 1-hour aggregates for 365 days
CREATE MATERIALIZED VIEW IF NOT EXISTS media_image_vision_annotations_10min
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('10 minutes', timestamp) AS bucket,
    COUNT(*) as annotation_count,
    COUNT(DISTINCT object_class) as unique_objects,
    AVG(confidence_score) as avg_confidence,
    MIN(timestamp) as first_annotation,
    MAX(timestamp) as last_annotation
FROM media_image_vision_annotations_raw
GROUP BY device_id, bucket;

CREATE MATERIALIZED VIEW IF NOT EXISTS media_image_vision_annotations_1hour
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 hour', bucket) AS bucket,
    SUM(annotation_count) as total_annotations,
    SUM(unique_objects) as total_unique_objects,
    AVG(avg_confidence) as avg_confidence,
    MIN(first_annotation) as first_annotation,
    MAX(last_annotation) as last_annotation
FROM media_image_vision_annotations_10min
GROUP BY device_id, bucket;

-- Emotion scores: Full data for 30 days, then 1-hour aggregates for 365 days
CREATE MATERIALIZED VIEW IF NOT EXISTS analysis_audio_emotion_scores_1hour
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 hour', timestamp) AS bucket,
    COUNT(*) as emotion_count,
    AVG(valence_score) as avg_valence,
    AVG(arousal_score) as avg_arousal,
    AVG(dominance_score) as avg_dominance,
    mode() WITHIN GROUP (ORDER BY predicted_emotion) as dominant_emotion,
    MIN(timestamp) as first_emotion,
    MAX(timestamp) as last_emotion
FROM analysis_audio_emotion_scores_raw
GROUP BY device_id, bucket;

-- Face emotions: Full data for 30 days, then 1-hour aggregates for 365 days
CREATE MATERIALIZED VIEW IF NOT EXISTS analysis_image_face_emotions_1hour
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 hour', timestamp) AS bucket,
    COUNT(*) as face_count,
    AVG(confidence_score) as avg_confidence,
    mode() WITHIN GROUP (ORDER BY emotion_label) as dominant_emotion,
    COUNT(DISTINCT face_id) as unique_faces,
    MIN(timestamp) as first_detection,
    MAX(timestamp) as last_detection
FROM analysis_image_face_emotions_raw
GROUP BY device_id, bucket;

-- Reasoning chains: Full data for 90 days, then daily aggregates for 2 years
CREATE MATERIALIZED VIEW IF NOT EXISTS analysis_context_reasoning_chains_1day
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 day', timestamp) AS bucket,
    COUNT(*) as reasoning_count,
    COUNT(DISTINCT context_type) as unique_contexts,
    AVG(confidence_score) as avg_confidence,
    string_agg(DISTINCT key_topics, '|') as daily_topics,
    MIN(timestamp) as first_reasoning,
    MAX(timestamp) as last_reasoning
FROM analysis_context_reasoning_chains_raw
GROUP BY device_id, bucket;

-- URL processed content: Full data for 180 days, then daily aggregates for 2 years
CREATE MATERIALIZED VIEW IF NOT EXISTS task_url_processed_content_1day
WITH (timescaledb.continuous) AS
SELECT
    device_id,
    time_bucket('1 day', timestamp) AS bucket,
    COUNT(*) as url_count,
    COUNT(DISTINCT domain) as unique_domains,
    COUNT(DISTINCT content_type) as content_types,
    string_agg(DISTINCT category, ',') as categories,
    MIN(timestamp) as first_url,
    MAX(timestamp) as last_url
FROM task_url_processed_content_raw
GROUP BY device_id, bucket;

-- Configure refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('media_audio_voice_segments_1min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

SELECT add_continuous_aggregate_policy('media_audio_voice_segments_1hour',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('media_text_word_timestamps_5min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

SELECT add_continuous_aggregate_policy('media_text_word_timestamps_1hour',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('media_image_vision_annotations_10min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes');

SELECT add_continuous_aggregate_policy('media_image_vision_annotations_1hour',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('analysis_audio_emotion_scores_1hour',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('analysis_image_face_emotions_1hour',
    start_offset => INTERVAL '4 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('analysis_context_reasoning_chains_1day',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

SELECT add_continuous_aggregate_policy('task_url_processed_content_1day',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Add hierarchical retention policies
-- Drop raw data after specified periods, but keep aggregates longer

-- Voice segments: Raw for 7 days, 1-min aggregates for 30 days, 1-hour aggregates for 365 days
SELECT add_retention_policy('media_audio_voice_segments_raw', INTERVAL '7 days');
SELECT add_retention_policy('media_audio_voice_segments_1min', INTERVAL '30 days');
SELECT add_retention_policy('media_audio_voice_segments_1hour', INTERVAL '365 days');

-- Word timestamps: Raw for 15 days, 5-min aggregates for 90 days, 1-hour aggregates for 365 days
SELECT add_retention_policy('media_text_word_timestamps_raw', INTERVAL '15 days');
SELECT add_retention_policy('media_text_word_timestamps_5min', INTERVAL '90 days');
SELECT add_retention_policy('media_text_word_timestamps_1hour', INTERVAL '365 days');

-- Vision annotations: Raw for 15 days, 10-min aggregates for 90 days, 1-hour aggregates for 365 days
SELECT add_retention_policy('media_image_vision_annotations_raw', INTERVAL '15 days');
SELECT add_retention_policy('media_image_vision_annotations_10min', INTERVAL '90 days');
SELECT add_retention_policy('media_image_vision_annotations_1hour', INTERVAL '365 days');

-- Emotion scores: Raw for 30 days, 1-hour aggregates for 365 days
SELECT add_retention_policy('analysis_audio_emotion_scores_raw', INTERVAL '30 days');
SELECT add_retention_policy('analysis_audio_emotion_scores_1hour', INTERVAL '365 days');

-- Face emotions: Raw for 30 days, 1-hour aggregates for 365 days
SELECT add_retention_policy('analysis_image_face_emotions_raw', INTERVAL '30 days');
SELECT add_retention_policy('analysis_image_face_emotions_1hour', INTERVAL '365 days');

-- Reasoning chains: Raw for 90 days, daily aggregates for 2 years
SELECT add_retention_policy('analysis_context_reasoning_chains_raw', INTERVAL '90 days');
SELECT add_retention_policy('analysis_context_reasoning_chains_1day', INTERVAL '730 days');

-- URL processed content: Raw for 180 days, daily aggregates for 2 years
SELECT add_retention_policy('task_url_processed_content_raw', INTERVAL '180 days');
SELECT add_retention_policy('task_url_processed_content_1day', INTERVAL '730 days');

-- Show configured retention policies
SELECT
    hypertable_name,
    (SELECT drop_after FROM timescaledb_information.jobs
     WHERE hypertable_name = h.hypertable_name AND proc_name = 'policy_retention' LIMIT 1) as retention_period
FROM timescaledb_information.hypertables h
WHERE hypertable_name LIKE 'media_%' OR hypertable_name LIKE 'analysis_%' OR hypertable_name LIKE 'task_%'
ORDER BY hypertable_name;
