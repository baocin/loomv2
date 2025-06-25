-- Migration 005: Create Processed Data Tables
-- Description: Creates hypertables for AI-processed data

-- Voice Activity Detection Results
CREATE TABLE IF NOT EXISTS media_audio_vad_filtered (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_timestamp TIMESTAMPTZ NOT NULL, -- Original audio timestamp
    has_speech BOOLEAN NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    audio_segment TEXT NOT NULL, -- Base64 encoded audio segment with speech
    segment_start_ms INT NOT NULL,
    segment_duration_ms INT NOT NULL,
    processing_model TEXT NOT NULL DEFAULT 'silero_vad',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Speech-to-Text Transcription Results
CREATE TABLE IF NOT EXISTS media_text_transcribed_words (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_timestamp TIMESTAMPTZ NOT NULL, -- VAD audio timestamp
    word TEXT NOT NULL,
    start_time_ms INT NOT NULL,
    end_time_ms INT NOT NULL,
    confidence DOUBLE PRECISION,
    speaker_id TEXT,
    processing_model TEXT NOT NULL DEFAULT 'nvidia_parakeet_tdt',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, start_time_ms)
);

-- Vision Analysis Results (MiniCPM)
CREATE TABLE IF NOT EXISTS media_image_analysis_minicpm_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_type TEXT NOT NULL, -- 'camera', 'screen'
    source_timestamp TIMESTAMPTZ NOT NULL,
    objects_detected TEXT[], -- Array of detected objects
    text_extracted TEXT,
    scene_description TEXT,
    confidence_scores JSONB, -- {"object1": 0.95, "object2": 0.87}
    bounding_boxes JSONB, -- [{"object": "person", "box": [x,y,w,h]}]
    processing_model TEXT NOT NULL DEFAULT 'minicpm_llama3_v25',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Speech Emotion Recognition Results
CREATE TABLE IF NOT EXISTS analysis_audio_emotion_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_timestamp TIMESTAMPTZ NOT NULL, -- VAD audio timestamp
    primary_emotion TEXT NOT NULL, -- happy, sad, angry, neutral, etc.
    emotion_scores JSONB NOT NULL, -- {"happy": 0.8, "sad": 0.1, ...}
    arousal DOUBLE PRECISION, -- -1 to 1 (calm to excited)
    valence DOUBLE PRECISION, -- -1 to 1 (negative to positive)
    processing_model TEXT NOT NULL DEFAULT 'laion_bud_e_whisper',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Face Emotion Recognition Results
CREATE TABLE IF NOT EXISTS analysis_image_emotion_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_timestamp TIMESTAMPTZ NOT NULL, -- Image analysis timestamp
    face_id TEXT NOT NULL, -- Unique ID for detected face
    primary_emotion TEXT NOT NULL,
    emotion_scores JSONB NOT NULL,
    face_landmarks JSONB, -- Facial landmark coordinates
    age_estimate INT,
    gender_estimate TEXT,
    processing_model TEXT NOT NULL DEFAULT 'laion_empathic_insight_face',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, face_id)
);

-- High-Level Context Inference Results (Mistral)
CREATE TABLE IF NOT EXISTS analysis_inferred_context_mistral_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    context_window_start TIMESTAMPTZ NOT NULL,
    context_window_end TIMESTAMPTZ NOT NULL,
    activity_summary TEXT NOT NULL,
    location_context TEXT,
    social_context TEXT,
    work_context TEXT,
    health_insights TEXT,
    mood_summary TEXT,
    recommendations TEXT[],
    confidence_scores JSONB,
    source_data_types TEXT[], -- ['transcription', 'vision', 'sensors']
    processing_model TEXT NOT NULL DEFAULT 'mistral_small_32',
    processing_version TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- URL Processing Results
CREATE TABLE IF NOT EXISTS task_url_processed_results (
    id BIGSERIAL,
    url TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_type TEXT NOT NULL, -- 'twitter', 'pdf', 'webpage'
    title TEXT,
    content_text TEXT,
    content_summary TEXT,
    extracted_entities JSONB, -- {"people": [...], "organizations": [...]}
    extracted_links TEXT[],
    processing_status TEXT NOT NULL, -- 'success', 'partial', 'failed'
    processing_model TEXT,
    processing_version TEXT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (url, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('media_audio_vad_filtered', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('media_text_transcribed_words', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('media_image_analysis_minicpm_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_audio_emotion_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_image_emotion_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_inferred_context_mistral_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('task_url_processed_results', 'timestamp', if_not_exists => TRUE);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_vad_device_time ON media_audio_vad_filtered (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vad_has_speech ON media_audio_vad_filtered (has_speech);
CREATE INDEX IF NOT EXISTS idx_transcribed_device_time ON media_text_transcribed_words (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transcribed_word ON media_text_transcribed_words USING GIN (to_tsvector('english', word));
CREATE INDEX IF NOT EXISTS idx_vision_device_time ON media_image_analysis_minicpm_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vision_objects ON media_image_analysis_minicpm_results USING GIN (objects_detected);
CREATE INDEX IF NOT EXISTS idx_audio_emotion_device_time ON analysis_audio_emotion_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_image_emotion_device_time ON analysis_image_emotion_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_context_device_time ON analysis_inferred_context_mistral_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_url_processed_url ON task_url_processed_results (url);

-- Configure compression for processed data tables (longer retention as they're smaller)
ALTER TABLE media_audio_vad_filtered SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('media_audio_vad_filtered', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE media_text_transcribed_words SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('media_text_transcribed_words', INTERVAL '14 days', if_not_exists => TRUE);

ALTER TABLE media_image_analysis_minicpm_results SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('media_image_analysis_minicpm_results', INTERVAL '14 days', if_not_exists => TRUE);

-- Add retention policies for processed data (longer than raw data)
SELECT add_retention_policy('media_audio_vad_filtered', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('media_text_transcribed_words', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('media_image_analysis_minicpm_results', INTERVAL '60 days', if_not_exists => TRUE);
SELECT add_retention_policy('analysis_audio_emotion_results', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('analysis_image_emotion_results', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('analysis_inferred_context_mistral_results', INTERVAL '180 days', if_not_exists => TRUE);
SELECT add_retention_policy('task_url_processed_results', INTERVAL '365 days', if_not_exists => TRUE);
