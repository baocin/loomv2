-- Migration 015: Create Analysis Result Tables
-- Description: Creates tables for AI analysis results

-- Analysis Transcription Results Table
CREATE TABLE IF NOT EXISTS analysis_transcription_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_audio_id TEXT NOT NULL,
    transcript_text TEXT NOT NULL,
    word_timestamps JSONB,
    confidence DOUBLE PRECISION,
    language TEXT,
    model_version TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Analysis Image Recognition Results Table
CREATE TABLE IF NOT EXISTS analysis_image_recognition_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    source_image_id TEXT NOT NULL,
    caption TEXT,
    objects_detected JSONB,
    faces_detected JSONB,
    text_extracted TEXT,
    model_version TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Analysis Context Inference Results Table
CREATE TABLE IF NOT EXISTS analysis_context_inference_results (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    context_type TEXT NOT NULL,
    inferred_activity TEXT,
    confidence DOUBLE PRECISION,
    supporting_evidence JSONB,
    model_version TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('analysis_transcription_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_image_recognition_results', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('analysis_context_inference_results', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transcription_device_time ON analysis_transcription_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_image_recognition_device_time ON analysis_image_recognition_results (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_context_inference_device_time ON analysis_context_inference_results (device_id, timestamp DESC);
