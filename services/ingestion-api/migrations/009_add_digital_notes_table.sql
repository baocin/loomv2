-- Create table for raw digital notes

CREATE TABLE IF NOT EXISTS digital_notes_raw (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(255) NOT NULL,
    trace_id VARCHAR(255) NOT NULL,
    schema_version VARCHAR(50),
    note_id VARCHAR(255) NOT NULL,
    source_app VARCHAR(100),  -- Apple Notes, Google Keep, Obsidian, etc.
    title TEXT,
    content TEXT NOT NULL,
    has_images BOOLEAN DEFAULT FALSE,
    image_urls TEXT[],
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    metadata JSONB,
    created_at_db TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable with 7 day chunks
SELECT create_hypertable('digital_notes_raw', 'time', 
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_digital_notes_device_time 
    ON digital_notes_raw (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_digital_notes_note_id 
    ON digital_notes_raw (note_id);
CREATE INDEX IF NOT EXISTS idx_digital_notes_source_app 
    ON digital_notes_raw (source_app);

-- Set retention policy (optional)
-- SELECT add_retention_policy('digital_notes_raw', INTERVAL '1 year');