-- Migration 018: Create AI Processing Result Tables
-- Description: Creates TimescaleDB hypertables for AI processing results with automatic Kafka ingestion

-- Voice Segments Table (from VAD processing)
CREATE TABLE IF NOT EXISTS media_audio_voice_segments_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    segment_start_time TIMESTAMPTZ NOT NULL,
    segment_end_time TIMESTAMPTZ NOT NULL,
    duration_ms INTEGER NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    audio_sample_rate INTEGER,
    audio_channels INTEGER DEFAULT 1,
    voice_activity_threshold REAL,
    segment_audio_data BYTEA, -- Optional: store the audio segment
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, timestamp)
);

-- Word Timestamps Table (from STT processing)
CREATE TABLE IF NOT EXISTS media_text_word_timestamps_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    word_sequence INTEGER NOT NULL,
    word_text TEXT NOT NULL,
    start_time_ms INTEGER NOT NULL,
    end_time_ms INTEGER NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    speaker_id TEXT,
    language_code TEXT DEFAULT 'en',
    phonetic_transcription TEXT,
    word_boundaries JSONB, -- Detailed timing info
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, word_sequence, timestamp)
);

-- Vision Annotations Table (from MiniCPM processing)
CREATE TABLE IF NOT EXISTS media_image_vision_annotations_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    annotation_id TEXT NOT NULL,
    object_class TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    bounding_box JSONB, -- {x, y, width, height}
    object_attributes JSONB, -- Color, size, etc.
    ocr_text TEXT,
    scene_description TEXT,
    image_width INTEGER,
    image_height INTEGER,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, annotation_id, timestamp)
);

-- Audio Emotion Scores Table (from emotion analysis)
CREATE TABLE IF NOT EXISTS analysis_audio_emotion_scores_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    predicted_emotion TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    valence_score REAL CHECK (valence_score >= -1 AND valence_score <= 1),
    arousal_score REAL CHECK (arousal_score >= -1 AND arousal_score <= 1),
    dominance_score REAL CHECK (dominance_score >= -1 AND dominance_score <= 1),
    emotion_probabilities JSONB, -- All emotion class probabilities
    audio_features JSONB, -- Extracted audio features
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, segment_id, timestamp)
);

-- Face Emotions Table (from face emotion analysis)
CREATE TABLE IF NOT EXISTS analysis_image_face_emotions_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    face_id TEXT NOT NULL,
    emotion_label TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    face_bounding_box JSONB, -- {x, y, width, height}
    facial_landmarks JSONB, -- Key facial points
    age_estimate INTEGER,
    gender_estimate TEXT,
    emotion_intensities JSONB, -- All emotion scores
    face_quality_score REAL,
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, face_id, timestamp)
);

-- Context Reasoning Chains Table (from Mistral processing)
CREATE TABLE IF NOT EXISTS analysis_context_reasoning_chains_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    reasoning_id TEXT NOT NULL,
    context_type TEXT NOT NULL, -- 'conversation', 'activity', 'location', etc.
    reasoning_chain JSONB NOT NULL, -- Step-by-step reasoning process
    conclusion_text TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    input_sources JSONB, -- References to source data
    key_topics TEXT[],
    entities_mentioned JSONB, -- Named entities, people, places
    temporal_context JSONB, -- Time-based context info
    spatial_context JSONB, -- Location-based context info
    model_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, reasoning_id, timestamp)
);

-- URL Processed Content Table (from URL processing)
CREATE TABLE IF NOT EXISTS task_url_processed_content_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    message_id TEXT NOT NULL,
    url_id TEXT NOT NULL,
    original_url TEXT NOT NULL,
    final_url TEXT, -- After redirects
    domain TEXT NOT NULL,
    content_type TEXT NOT NULL, -- 'twitter', 'pdf', 'webpage', 'github'
    title TEXT,
    content_text TEXT,
    content_summary TEXT,
    extracted_metadata JSONB,
    content_length INTEGER,
    language_detected TEXT,
    category TEXT,
    tags TEXT[],
    processing_duration_ms INTEGER,
    processor_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, message_id, url_id, timestamp)
);

-- Create hypertables for all result tables
SELECT create_hypertable('media_audio_voice_segments_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('media_text_word_timestamps_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('media_image_vision_annotations_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_audio_emotion_scores_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_image_face_emotions_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_context_reasoning_chains_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('task_url_processed_content_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_voice_segments_confidence ON media_audio_voice_segments_raw (confidence_score, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_voice_segments_duration ON media_audio_voice_segments_raw (duration_ms, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_word_timestamps_text ON media_text_word_timestamps_raw (word_text, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_word_timestamps_speaker ON media_text_word_timestamps_raw (speaker_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_word_timestamps_confidence ON media_text_word_timestamps_raw (confidence_score, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_vision_annotations_class ON media_image_vision_annotations_raw (object_class, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vision_annotations_confidence ON media_image_vision_annotations_raw (confidence_score, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vision_annotations_ocr ON media_image_vision_annotations_raw USING GIN (to_tsvector('english', ocr_text));

CREATE INDEX IF NOT EXISTS idx_emotion_scores_emotion ON analysis_audio_emotion_scores_raw (predicted_emotion, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_scores_valence ON analysis_audio_emotion_scores_raw (valence_score, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_face_emotions_emotion ON analysis_image_face_emotions_raw (emotion_label, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_face_emotions_age ON analysis_image_face_emotions_raw (age_estimate, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_reasoning_context_type ON analysis_context_reasoning_chains_raw (context_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_reasoning_topics ON analysis_context_reasoning_chains_raw USING GIN (key_topics);
CREATE INDEX IF NOT EXISTS idx_reasoning_conclusion ON analysis_context_reasoning_chains_raw USING GIN (to_tsvector('english', conclusion_text));

CREATE INDEX IF NOT EXISTS idx_url_content_domain ON task_url_processed_content_raw (domain, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_url_content_type ON task_url_processed_content_raw (content_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_url_content_category ON task_url_processed_content_raw (category, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_url_content_text ON task_url_processed_content_raw USING GIN (to_tsvector('english', content_text));

-- Configure compression for result tables
ALTER TABLE media_audio_voice_segments_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE media_text_word_timestamps_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,speaker_id',
    timescaledb.compress_orderby = 'timestamp DESC, word_sequence'
);

ALTER TABLE media_image_vision_annotations_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,object_class',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE analysis_audio_emotion_scores_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,predicted_emotion',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE analysis_image_face_emotions_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,emotion_label',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE analysis_context_reasoning_chains_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,context_type',
    timescaledb.compress_orderby = 'timestamp DESC'
);

ALTER TABLE task_url_processed_content_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'device_id,content_type',
    timescaledb.compress_orderby = 'timestamp DESC'
);

-- Add compression policies (compress after specified time)
SELECT add_compression_policy('media_audio_voice_segments_raw', INTERVAL '1 day');
SELECT add_compression_policy('media_text_word_timestamps_raw', INTERVAL '3 days');
SELECT add_compression_policy('media_image_vision_annotations_raw', INTERVAL '3 days');
SELECT add_compression_policy('analysis_audio_emotion_scores_raw', INTERVAL '7 days');
SELECT add_compression_policy('analysis_image_face_emotions_raw', INTERVAL '7 days');
SELECT add_compression_policy('analysis_context_reasoning_chains_raw', INTERVAL '14 days');
SELECT add_compression_policy('task_url_processed_content_raw', INTERVAL '30 days');

-- Show created tables and their configurations
SELECT
    hypertable_name,
    compression_enabled,
    (SELECT compress_after FROM timescaledb_information.jobs
     WHERE hypertable_name = h.hypertable_name AND proc_name = 'policy_compression' LIMIT 1) as compress_after
FROM timescaledb_information.hypertables h
WHERE hypertable_name LIKE 'media_%' OR hypertable_name LIKE 'analysis_%' OR hypertable_name LIKE 'task_%'
ORDER BY hypertable_name;
