-- Migration 020: Create embedding storage tables for Nomic Embed Vision service
-- Description: Tables for storing text and image embeddings with vector search capabilities
-- Created: 2025-01-24

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Text embeddings table
CREATE TABLE embeddings_text_nomic (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_id TEXT NOT NULL,
    
    -- Text content and metadata
    text_content TEXT NOT NULL,
    text_length INTEGER NOT NULL,
    source_topic TEXT NOT NULL,
    source_message_id TEXT NOT NULL,
    
    -- Embedding data
    embedding vector(768) NOT NULL, -- Nomic Embed Vision dimension
    embedding_model TEXT NOT NULL DEFAULT 'nomic-ai/nomic-embed-vision-v1.5',
    embedding_dimension INTEGER NOT NULL DEFAULT 768,
    processing_time_ms FLOAT,
    
    -- Metadata
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_device_id CHECK (device_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    CONSTRAINT valid_text_length CHECK (text_length > 0),
    CONSTRAINT valid_embedding_dimension CHECK (embedding_dimension = 768),
    CONSTRAINT valid_processing_time CHECK (processing_time_ms >= 0)
);

-- Image embeddings table
CREATE TABLE embeddings_image_nomic (
    id BIGSERIAL PRIMARY KEY,
    device_id TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_id TEXT NOT NULL,
    
    -- Image metadata
    image_format TEXT NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    image_size_bytes INTEGER NOT NULL,
    source_topic TEXT NOT NULL,
    source_message_id TEXT NOT NULL,
    
    -- Embedding data
    embedding vector(768) NOT NULL, -- Nomic Embed Vision dimension
    embedding_model TEXT NOT NULL DEFAULT 'nomic-ai/nomic-embed-vision-v1.5',
    embedding_dimension INTEGER NOT NULL DEFAULT 768,
    processing_time_ms FLOAT,
    
    -- Optional AI-generated description
    image_description TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- Constraints
    CONSTRAINT valid_device_id CHECK (device_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'),
    CONSTRAINT valid_image_dimensions CHECK (image_width > 0 AND image_height > 0),
    CONSTRAINT valid_image_size CHECK (image_size_bytes > 0),
    CONSTRAINT valid_embedding_dimension CHECK (embedding_dimension = 768),
    CONSTRAINT valid_processing_time CHECK (processing_time_ms >= 0)
);

-- Convert to TimescaleDB hypertables for time-series optimization
SELECT create_hypertable('embeddings_text_nomic', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    create_default_indexes => FALSE
);

SELECT create_hypertable('embeddings_image_nomic', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    create_default_indexes => FALSE
);

-- Create indexes for efficient querying

-- Text embeddings indexes
CREATE INDEX idx_embeddings_text_nomic_device_time 
    ON embeddings_text_nomic (device_id, timestamp DESC);

CREATE INDEX idx_embeddings_text_nomic_source 
    ON embeddings_text_nomic (source_topic, timestamp DESC);

CREATE INDEX idx_embeddings_text_nomic_content_search 
    ON embeddings_text_nomic USING gin(to_tsvector('english', text_content));

-- Vector similarity search index (HNSW for fast approximate nearest neighbor)
CREATE INDEX idx_embeddings_text_nomic_embedding_cosine 
    ON embeddings_text_nomic USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Image embeddings indexes
CREATE INDEX idx_embeddings_image_nomic_device_time 
    ON embeddings_image_nomic (device_id, timestamp DESC);

CREATE INDEX idx_embeddings_image_nomic_source 
    ON embeddings_image_nomic (source_topic, timestamp DESC);

CREATE INDEX idx_embeddings_image_nomic_dimensions 
    ON embeddings_image_nomic (image_width, image_height);

-- Vector similarity search index
CREATE INDEX idx_embeddings_image_nomic_embedding_cosine 
    ON embeddings_image_nomic USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Description search index
CREATE INDEX idx_embeddings_image_nomic_description_search 
    ON embeddings_image_nomic USING gin(to_tsvector('english', image_description))
    WHERE image_description IS NOT NULL;

-- Configure compression policies for storage efficiency
-- Compress chunks older than 7 days
SELECT add_compression_policy('embeddings_text_nomic', INTERVAL '7 days');
SELECT add_compression_policy('embeddings_image_nomic', INTERVAL '7 days');

-- Configure retention policies
-- Keep text embeddings for 1 year (they're valuable for semantic search)
SELECT add_retention_policy('embeddings_text_nomic', INTERVAL '1 year');

-- Keep image embeddings for 6 months (larger storage footprint)
SELECT add_retention_policy('embeddings_image_nomic', INTERVAL '6 months');

-- Create materialized view for embedding statistics
CREATE MATERIALIZED VIEW embedding_stats_hourly AS
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    COUNT(*) as total_embeddings,
    COUNT(*) FILTER (WHERE source_topic LIKE 'device.text%') as text_from_device,
    COUNT(*) FILTER (WHERE source_topic LIKE 'media.text%') as text_from_media,
    COUNT(*) FILTER (WHERE source_topic LIKE 'task.%') as text_from_tasks,
    AVG(processing_time_ms) as avg_processing_time_ms,
    AVG(text_length) as avg_text_length
FROM embeddings_text_nomic
GROUP BY hour
ORDER BY hour DESC;

CREATE UNIQUE INDEX ON embedding_stats_hourly (hour);

-- Refresh policy for the materialized view
SELECT add_continuous_aggregate_policy('embedding_stats_hourly',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Create function for semantic search
CREATE OR REPLACE FUNCTION semantic_search_text(
    query_embedding vector(768),
    similarity_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10,
    device_filter text DEFAULT NULL,
    time_range_hours integer DEFAULT NULL
) RETURNS TABLE (
    id bigint,
    device_id text,
    text_content text,
    similarity float,
    timestamp timestamptz,
    source_topic text,
    metadata jsonb
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.device_id,
        e.text_content,
        1 - (e.embedding <=> query_embedding) as similarity,
        e.timestamp,
        e.source_topic,
        e.metadata
    FROM embeddings_text_nomic e
    WHERE 
        (device_filter IS NULL OR e.device_id = device_filter)
        AND (time_range_hours IS NULL OR e.timestamp >= NOW() - INTERVAL '1 hour' * time_range_hours)
        AND (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT max_results;
END;
$$;

-- Create function for image semantic search
CREATE OR REPLACE FUNCTION semantic_search_images(
    query_embedding vector(768),
    similarity_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10,
    device_filter text DEFAULT NULL,
    time_range_hours integer DEFAULT NULL
) RETURNS TABLE (
    id bigint,
    device_id text,
    image_format text,
    image_width integer,
    image_height integer,
    image_description text,
    similarity float,
    timestamp timestamptz,
    source_topic text,
    metadata jsonb
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.device_id,
        e.image_format,
        e.image_width,
        e.image_height,
        e.image_description,
        1 - (e.embedding <=> query_embedding) as similarity,
        e.timestamp,
        e.source_topic,
        e.metadata
    FROM embeddings_image_nomic e
    WHERE 
        (device_filter IS NULL OR e.device_id = device_filter)
        AND (time_range_hours IS NULL OR e.timestamp >= NOW() - INTERVAL '1 hour' * time_range_hours)
        AND (1 - (e.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT max_results;
END;
$$;