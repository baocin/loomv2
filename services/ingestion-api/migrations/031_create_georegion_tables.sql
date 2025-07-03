-- Migration 031: Create Georegion Detection Tables
-- Description: Creates tables for georegion definitions and detection results

-- Table for storing georegion definitions
CREATE TABLE IF NOT EXISTS georegions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    center_latitude DOUBLE PRECISION NOT NULL,
    center_longitude DOUBLE PRECISION NOT NULL,
    radius_meters DOUBLE PRECISION NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('home', 'work', 'custom')),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for storing georegion detection results
CREATE TABLE IF NOT EXISTS location_georegion_detected (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    georegion_id INTEGER NOT NULL REFERENCES georegions(id),
    georegion_name TEXT NOT NULL,
    georegion_type TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('enter', 'exit', 'dwell')),
    confidence DOUBLE PRECISION,
    distance_from_center_meters DOUBLE PRECISION,
    source_latitude DOUBLE PRECISION,
    source_longitude DOUBLE PRECISION,
    source_accuracy DOUBLE PRECISION,
    dwell_time_seconds INTEGER, -- Only for 'dwell' events
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Table for storing geocoded addresses
CREATE TABLE IF NOT EXISTS location_address_geocoded (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    formatted_address TEXT,
    street_number TEXT,
    street_name TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    postal_code TEXT,
    geocoding_service TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Convert tables to hypertables (except georegions which is a reference table)
SELECT create_hypertable('location_georegion_detected', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('location_address_geocoded', 'timestamp', if_not_exists => TRUE);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_georegion_detected_device_time ON location_georegion_detected (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_georegion_detected_georegion ON location_georegion_detected (georegion_id);
CREATE INDEX IF NOT EXISTS idx_georegion_detected_event_type ON location_georegion_detected (event_type);
CREATE INDEX IF NOT EXISTS idx_georegion_detected_type ON location_georegion_detected (georegion_type);

CREATE INDEX IF NOT EXISTS idx_address_geocoded_device_time ON location_address_geocoded (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_address_geocoded_location ON location_address_geocoded (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_address_geocoded_city ON location_address_geocoded (city);

-- Create spatial index on georegions for efficient proximity queries
CREATE INDEX IF NOT EXISTS idx_georegions_location ON georegions (center_latitude, center_longitude);

-- Insert default georegions (example - these should be customized)
INSERT INTO georegions (name, description, center_latitude, center_longitude, radius_meters, type) VALUES
    ('Home', 'Home location', 37.7749, -122.4194, 100, 'home'),  -- Example: San Francisco
    ('Work', 'Work location', 37.7955, -122.3937, 150, 'work'),  -- Example: Financial District
    ('Gym', 'Fitness center', 37.7900, -122.4090, 50, 'custom')  -- Example: Custom location
ON CONFLICT (name) DO NOTHING;

-- Configure compression for TimescaleDB tables
ALTER TABLE location_georegion_detected SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('location_georegion_detected', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE location_address_geocoded SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'timestamp DESC',
    timescaledb.compress_segmentby = 'device_id'
);
SELECT add_compression_policy('location_address_geocoded', INTERVAL '14 days', if_not_exists => TRUE);

-- Add retention policies
SELECT add_retention_policy('location_georegion_detected', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('location_address_geocoded', INTERVAL '180 days', if_not_exists => TRUE);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_georegions_updated_at BEFORE UPDATE ON georegions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();