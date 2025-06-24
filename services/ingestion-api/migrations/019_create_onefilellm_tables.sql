-- Migration 019: Create OneFileLLM processed data tables
-- Description: Tables for storing processed GitHub repositories and documents from OneFileLLM

-- Processed GitHub repositories table
CREATE TABLE IF NOT EXISTS processed_github_parsed (
    id BIGSERIAL PRIMARY KEY,
    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    device_id UUID NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_id UUID NOT NULL UNIQUE,

    -- GitHub-specific fields
    original_url TEXT NOT NULL,
    repository_name VARCHAR(255) NOT NULL, -- owner/repo format
    repository_type VARCHAR(50) NOT NULL DEFAULT 'repository', -- repository, file, issue, pr
    aggregated_content TEXT NOT NULL, -- OneFileLLM output
    content_summary TEXT NOT NULL,
    file_count INTEGER NOT NULL DEFAULT 0,
    total_size_bytes BIGINT NOT NULL DEFAULT 0,
    processing_duration_ms INTEGER NOT NULL,

    -- Processing metadata
    files_processed JSONB NOT NULL DEFAULT '[]',
    files_skipped JSONB NOT NULL DEFAULT '[]',
    extraction_metadata JSONB NOT NULL DEFAULT '{}',
    onefilellm_version VARCHAR(50) NOT NULL DEFAULT 'unknown',

    -- Indexing
    CONSTRAINT valid_file_count CHECK (file_count >= 0),
    CONSTRAINT valid_size CHECK (total_size_bytes >= 0),
    CONSTRAINT valid_duration CHECK (processing_duration_ms >= 0)
);

-- Create indexes for processed_github_parsed
CREATE INDEX IF NOT EXISTS idx_processed_github_device_timestamp
    ON processed_github_parsed (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_processed_github_repository
    ON processed_github_parsed (repository_name);
CREATE INDEX IF NOT EXISTS idx_processed_github_type
    ON processed_github_parsed (repository_type);
CREATE INDEX IF NOT EXISTS idx_processed_github_url
    ON processed_github_parsed USING HASH (original_url);

-- Processed documents table
CREATE TABLE IF NOT EXISTS processed_document_parsed (
    id BIGSERIAL PRIMARY KEY,
    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    device_id UUID NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    message_id UUID NOT NULL UNIQUE,

    -- Document-specific fields
    original_filename VARCHAR(512) NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'general', -- pdf, docx, txt, markdown, html
    content_type VARCHAR(255) NOT NULL DEFAULT 'application/octet-stream',
    extracted_text TEXT NOT NULL,
    content_summary TEXT NOT NULL,
    original_size_bytes BIGINT NOT NULL,
    processing_duration_ms INTEGER NOT NULL,

    -- Text analysis fields
    extraction_method VARCHAR(50) NOT NULL,
    language_detected VARCHAR(10), -- ISO language code
    page_count INTEGER, -- For PDFs and similar
    word_count INTEGER NOT NULL DEFAULT 0,
    character_count INTEGER NOT NULL DEFAULT 0,

    -- Processing metadata
    extraction_metadata JSONB NOT NULL DEFAULT '{}',
    onefilellm_version VARCHAR(50) NOT NULL DEFAULT 'unknown',

    -- Indexing
    CONSTRAINT valid_original_size CHECK (original_size_bytes >= 0),
    CONSTRAINT valid_duration CHECK (processing_duration_ms >= 0),
    CONSTRAINT valid_word_count CHECK (word_count >= 0),
    CONSTRAINT valid_char_count CHECK (character_count >= 0),
    CONSTRAINT valid_page_count CHECK (page_count IS NULL OR page_count > 0)
);

-- Create indexes for processed_document_parsed
CREATE INDEX IF NOT EXISTS idx_processed_document_device_timestamp
    ON processed_document_parsed (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_processed_document_filename
    ON processed_document_parsed (original_filename);
CREATE INDEX IF NOT EXISTS idx_processed_document_type
    ON processed_document_parsed (document_type);
CREATE INDEX IF NOT EXISTS idx_processed_document_content_type
    ON processed_document_parsed (content_type);
CREATE INDEX IF NOT EXISTS idx_processed_document_language
    ON processed_document_parsed (language_detected);

-- Full-text search index for GitHub content
CREATE INDEX IF NOT EXISTS idx_processed_github_content_fts
    ON processed_github_parsed USING GIN (to_tsvector('english', aggregated_content));

-- Full-text search index for document content
CREATE INDEX IF NOT EXISTS idx_processed_document_content_fts
    ON processed_document_parsed USING GIN (to_tsvector('english', extracted_text));

-- Row Level Security (RLS) for processed_github_parsed
ALTER TABLE processed_github_parsed ENABLE ROW LEVEL SECURITY;

CREATE POLICY processed_github_device_isolation ON processed_github_parsed
    FOR ALL TO PUBLIC
    USING (device_id = current_setting('app.current_device_id', true)::UUID);

-- Row Level Security (RLS) for processed_document_parsed
ALTER TABLE processed_document_parsed ENABLE ROW LEVEL SECURITY;

CREATE POLICY processed_document_device_isolation ON processed_document_parsed
    FOR ALL TO PUBLIC
    USING (device_id = current_setting('app.current_device_id', true)::UUID);

-- Convert to TimescaleDB hypertables if TimescaleDB is enabled
DO $$
BEGIN
    -- Check if TimescaleDB extension is available
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        -- Create hypertables for time-series optimization
        PERFORM create_hypertable(
            'processed_github_parsed',
            'timestamp',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );

        PERFORM create_hypertable(
            'processed_document_parsed',
            'timestamp',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        );

        -- Add compression policies (compress after 1 day)
        PERFORM add_compression_policy(
            'processed_github_parsed',
            INTERVAL '1 day',
            if_not_exists => TRUE
        );

        PERFORM add_compression_policy(
            'processed_document_parsed',
            INTERVAL '1 day',
            if_not_exists => TRUE
        );

        -- Add retention policies (keep for 1 year)
        PERFORM add_retention_policy(
            'processed_github_parsed',
            INTERVAL '1 year',
            if_not_exists => TRUE
        );

        PERFORM add_retention_policy(
            'processed_document_parsed',
            INTERVAL '1 year',
            if_not_exists => TRUE
        );

        RAISE NOTICE 'Created TimescaleDB hypertables for OneFileLLM processed data';
    ELSE
        RAISE NOTICE 'TimescaleDB not available, using regular PostgreSQL tables';
    END IF;
END
$$;
