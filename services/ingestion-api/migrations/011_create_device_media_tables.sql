-- Migration 011: Create Device Media Tables
-- Description: Creates tables for media data (images, video, notes)

-- Device Image Camera Table
CREATE TABLE IF NOT EXISTS device_image_camera_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    image_data TEXT NOT NULL, -- Base64 encoded image
    format TEXT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    source TEXT, -- camera, screenshot, etc.
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Video Screen Table
CREATE TABLE IF NOT EXISTS device_video_screen_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    frame_number INT NOT NULL,
    frame_data TEXT NOT NULL, -- Base64 encoded frame
    format TEXT NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    fps DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, frame_number)
);

-- Device Text Notes Table
CREATE TABLE IF NOT EXISTS device_text_notes_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    note_content TEXT NOT NULL,
    note_type TEXT,
    word_count INT,
    character_count INT,
    language TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_image_camera_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_video_screen_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_text_notes_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_image_device_time ON device_image_camera_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_video_device_time ON device_video_screen_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_notes_device_time ON device_text_notes_raw (device_id, timestamp DESC);
