-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create emails with embeddings table
CREATE TABLE IF NOT EXISTS emails_with_embeddings (
    id SERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL UNIQUE,
    message_id TEXT,
    device_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),

    -- Email fields
    subject TEXT,
    sender_name TEXT,
    sender_email TEXT,
    recipient_email TEXT,
    body_text TEXT,
    body_html TEXT,
    headers JSONB,
    attachments JSONB,
    folder TEXT,
    email_source TEXT,

    -- Embedding fields
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim embeddings
    embedding_model TEXT,
    embedding_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Metadata
    metadata JSONB
);

-- Create indexes for emails
CREATE INDEX idx_emails_timestamp ON emails_with_embeddings (timestamp DESC);
CREATE INDEX idx_emails_sender ON emails_with_embeddings (sender_email);
CREATE INDEX idx_emails_device ON emails_with_embeddings (device_id);
CREATE INDEX idx_emails_embedding ON emails_with_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create Twitter likes with embeddings table
CREATE TABLE IF NOT EXISTS twitter_likes_with_embeddings (
    id SERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL UNIQUE,
    tweet_id TEXT NOT NULL UNIQUE,
    device_id TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    liked_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ DEFAULT NOW(),

    -- Tweet fields
    tweet_url TEXT,
    tweet_text TEXT,
    author_username TEXT,
    author_name TEXT,
    author_profile_url TEXT,

    -- Embedding fields
    embedding vector(384),
    embedding_model TEXT,
    embedding_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Screenshot/extraction reference
    screenshot_url TEXT,
    extracted_content JSONB,
    extraction_timestamp TIMESTAMPTZ,

    -- Metadata
    metadata JSONB
);

-- Create indexes for Twitter
CREATE INDEX idx_twitter_timestamp ON twitter_likes_with_embeddings (timestamp DESC);
CREATE INDEX idx_twitter_author ON twitter_likes_with_embeddings (author_username);
CREATE INDEX idx_twitter_device ON twitter_likes_with_embeddings (device_id);
CREATE INDEX idx_twitter_embedding ON twitter_likes_with_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create raw Twitter screenshot/extraction results table
CREATE TABLE IF NOT EXISTS twitter_extraction_results (
    id SERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL,
    tweet_id TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Screenshot data
    screenshot_path TEXT,
    screenshot_size_bytes INTEGER,
    screenshot_dimensions JSONB,

    -- Extracted content
    extracted_text TEXT,
    extracted_links JSONB,
    extracted_media JSONB,
    extracted_metadata JSONB,

    -- Processing metadata
    processor_version TEXT,
    processing_duration_ms INTEGER,
    error_message TEXT
);

CREATE INDEX idx_extraction_tweet_id ON twitter_extraction_results (tweet_id);
CREATE INDEX idx_extraction_trace_id ON twitter_extraction_results (trace_id);

-- Add functions for semantic search
CREATE OR REPLACE FUNCTION find_similar_emails(
    query_embedding vector(384),
    match_count integer DEFAULT 10
)
RETURNS TABLE (
    id integer,
    trace_id text,
    subject text,
    sender_email text,
    email_timestamp timestamptz,
    similarity float8
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.trace_id,
        e.subject,
        e.sender_email,
        e.timestamp as email_timestamp,
        1 - (e.embedding <=> query_embedding) as similarity
    FROM emails_with_embeddings e
    WHERE e.embedding IS NOT NULL
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION find_similar_tweets(
    query_embedding vector(384),
    match_count integer DEFAULT 10
)
RETURNS TABLE (
    id integer,
    trace_id text,
    tweet_id text,
    tweet_text text,
    author_username text,
    tweet_timestamp timestamptz,
    similarity float8
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.id,
        t.trace_id,
        t.tweet_id,
        t.tweet_text,
        t.author_username,
        t.timestamp as tweet_timestamp,
        1 - (t.embedding <=> query_embedding) as similarity
    FROM twitter_likes_with_embeddings t
    WHERE t.embedding IS NOT NULL
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
