-- Add tables for storing text embeddings from various sources

-- Create hypertable for notification embeddings
CREATE TABLE IF NOT EXISTS analysis_text_embedded_notifications (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(255) NOT NULL,
    notification_id VARCHAR(255),
    source VARCHAR(100),  -- app name or system
    title TEXT,
    content TEXT NOT NULL,
    embedding VECTOR(384),  -- For sentence-transformers/all-MiniLM-L6-v2
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable with 7 day chunks
SELECT create_hypertable('analysis_text_embedded_notifications', 'time', 
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notifications_device_time 
    ON analysis_text_embedded_notifications (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_source 
    ON analysis_text_embedded_notifications (source);
CREATE INDEX IF NOT EXISTS idx_notifications_embedding 
    ON analysis_text_embedded_notifications USING ivfflat (embedding vector_cosine_ops);

-- Create hypertable for notes embeddings
CREATE TABLE IF NOT EXISTS analysis_text_embedded_notes (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(255) NOT NULL,
    note_id VARCHAR(255),
    source VARCHAR(100),  -- app name (Apple Notes, Google Keep, etc)
    title TEXT,
    content TEXT NOT NULL,
    ocr_content TEXT,  -- If extracted via OCR from images
    embedding VECTOR(384),  -- For sentence-transformers/all-MiniLM-L6-v2
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable with 30 day chunks (notes are less frequent)
SELECT create_hypertable('analysis_text_embedded_notes', 'time', 
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notes_device_time 
    ON analysis_text_embedded_notes (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_notes_source 
    ON analysis_text_embedded_notes (source);
CREATE INDEX IF NOT EXISTS idx_notes_embedding 
    ON analysis_text_embedded_notes USING ivfflat (embedding vector_cosine_ops);

-- Set retention policies (optional - adjust as needed)
-- SELECT add_retention_policy('analysis_text_embedded_notifications', INTERVAL '90 days');
-- SELECT add_retention_policy('analysis_text_embedded_notes', INTERVAL '1 year');

-- Add compression policies for older data
SELECT add_compression_policy('analysis_text_embedded_notifications', INTERVAL '30 days');
SELECT add_compression_policy('analysis_text_embedded_notes', INTERVAL '90 days');