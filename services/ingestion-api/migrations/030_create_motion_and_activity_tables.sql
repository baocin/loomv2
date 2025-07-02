-- Migration: Create motion and activity classification tables
-- Description: Creates tables for significant motion events and activity classification

-- Create motion events significant table
CREATE TABLE IF NOT EXISTS motion_events_significant (
    event_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_seconds REAL,
    motion_type TEXT,
    confidence REAL,
    max_acceleration REAL,
    avg_acceleration REAL,
    dominant_axis TEXT,
    activity_type TEXT,
    activity_confidence REAL,
    sample_count INTEGER,
    raw_data_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id, timestamp)
);

-- Convert to hypertable if TimescaleDB is enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable(
            'motion_events_significant',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );
    END IF;
END $$;

-- Create motion classification activity table
CREATE TABLE IF NOT EXISTS motion_classification_activity (
    message_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT,
    activity_type TEXT,
    confidence REAL,
    location_context TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_seconds REAL,
    motion_events_count INTEGER,
    step_count INTEGER,
    distance_meters REAL,
    avg_speed_ms REAL,
    max_speed_ms REAL,
    start_location JSONB,
    end_location JSONB,
    metrics JSONB,
    source_events TEXT[],
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (message_id, timestamp)
);

-- Convert to hypertable if TimescaleDB is enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable(
            'motion_classification_activity',
            'timestamp',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );
    END IF;
END $$;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_motion_events_device_time ON motion_events_significant (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_motion_events_type ON motion_events_significant (motion_type);
CREATE INDEX IF NOT EXISTS idx_motion_events_confidence ON motion_events_significant (confidence);

CREATE INDEX IF NOT EXISTS idx_activity_device_time ON motion_classification_activity (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activity_type ON motion_classification_activity (activity_type);
CREATE INDEX IF NOT EXISTS idx_activity_confidence ON motion_classification_activity (confidence);

-- Add compression policy if TimescaleDB is enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Compress data older than 30 days
        PERFORM add_compression_policy('motion_events_significant', INTERVAL '30 days');
        PERFORM add_compression_policy('motion_classification_activity', INTERVAL '30 days');
    END IF;
EXCEPTION
    WHEN undefined_function THEN
        -- Compression not available in this TimescaleDB version
        RAISE NOTICE 'Compression policies not added - feature not available';
END $$;