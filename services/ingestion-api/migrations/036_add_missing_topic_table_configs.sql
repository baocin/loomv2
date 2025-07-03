-- Migration: Add missing topic-to-table configurations for kafka-to-db consumer
-- Purpose: Ensure media.text.transcribed.words and digital.notes.raw flow to database

-- First ensure the topics are registered in kafka_topics table
INSERT INTO kafka_topics (topic_name, category, source, datatype, stage, description, retention_days)
VALUES
    ('media.text.transcribed.words', 'media', 'text', 'transcribed', 'words', 'Word-by-word transcripts from speech-to-text processing', 90),
    ('digital.notes.raw', 'digital', 'notes', 'raw', NULL, 'Raw notes from digital note-taking apps', 365)
ON CONFLICT (topic_name) DO UPDATE
SET description = EXCLUDED.description,
    retention_days = EXCLUDED.retention_days,
    updated_at = NOW();

-- Add topic-to-table configuration for transcribed words
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('media.text.transcribed.words', 'media_text_transcribed_words', 'device_id, timestamp, start_time_ms', 'ignore')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    updated_at = NOW();

-- Add topic-to-table configuration for digital notes
INSERT INTO topic_table_configs (topic_name, table_name, upsert_key, conflict_strategy)
VALUES ('digital.notes.raw', 'digital_notes_raw', 'device_id, time, note_id', 'update')
ON CONFLICT (topic_name) DO UPDATE
SET table_name = EXCLUDED.table_name,
    upsert_key = EXCLUDED.upsert_key,
    conflict_strategy = EXCLUDED.conflict_strategy,
    updated_at = NOW();

-- Add field mappings for transcribed words
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'device_id', 'device_id', 'string', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'timestamp', 'timestamp', 'timestamp', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'schema_version', 'schema_version', 'string', false),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'source_timestamp', 'source_timestamp', 'timestamp', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'word', 'word', 'string', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'start_time_ms', 'start_time_ms', 'integer', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'end_time_ms', 'end_time_ms', 'integer', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'confidence', 'confidence', 'float', false),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'speaker_id', 'speaker_id', 'string', false),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'processing_model', 'processing_model', 'string', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'processing_version', 'processing_version', 'string', true),
    ('media.text.transcribed.words', 'media_text_transcribed_words', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Add field mappings for digital notes
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('digital.notes.raw', 'digital_notes_raw', 'device_id', 'device_id', 'string', true),
    ('digital.notes.raw', 'digital_notes_raw', 'timestamp', 'time', 'timestamp', true),
    ('digital.notes.raw', 'digital_notes_raw', 'trace_id', 'trace_id', 'string', true),
    ('digital.notes.raw', 'digital_notes_raw', 'schema_version', 'schema_version', 'string', false),
    ('digital.notes.raw', 'digital_notes_raw', 'note_id', 'note_id', 'string', true),
    ('digital.notes.raw', 'digital_notes_raw', 'source_app', 'source_app', 'string', false),
    ('digital.notes.raw', 'digital_notes_raw', 'title', 'title', 'string', false),
    ('digital.notes.raw', 'digital_notes_raw', 'content', 'content', 'string', true),
    ('digital.notes.raw', 'digital_notes_raw', 'has_images', 'has_images', 'boolean', false),
    ('digital.notes.raw', 'digital_notes_raw', 'image_urls', 'image_urls', 'array', false),
    ('digital.notes.raw', 'digital_notes_raw', 'created_at', 'created_at', 'timestamp', false),
    ('digital.notes.raw', 'digital_notes_raw', 'updated_at', 'updated_at', 'timestamp', false),
    ('digital.notes.raw', 'digital_notes_raw', 'metadata', 'metadata', 'json', false)
ON CONFLICT (topic_name, source_field_path, target_column) DO NOTHING;

-- Verify the configurations were added
SELECT
    ttc.topic_name,
    ttc.table_name,
    ttc.upsert_key,
    ttc.conflict_strategy,
    COUNT(tfm.id) as field_mappings_count
FROM topic_table_configs ttc
LEFT JOIN topic_field_mappings tfm ON ttc.topic_name = tfm.topic_name
WHERE ttc.topic_name IN ('media.text.transcribed.words', 'digital.notes.raw')
GROUP BY ttc.topic_name, ttc.table_name, ttc.upsert_key, ttc.conflict_strategy;

-- Also check which other topics are configured for kafka-to-db consumer
SELECT
    kt.topic_name,
    kt.category,
    kt.source,
    kt.datatype,
    ttc.table_name,
    CASE
        WHEN ttc.table_name IS NOT NULL THEN 'Configured'
        ELSE 'Not Configured'
    END as db_status
FROM kafka_topics kt
LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
WHERE kt.is_active = true
ORDER BY db_status DESC, kt.category, kt.source, kt.datatype;
