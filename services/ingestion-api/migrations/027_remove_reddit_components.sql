-- Migration: Remove Reddit Components
-- Description: Drop all Reddit-related tables and indexes as part of removing Reddit processing from the system
-- Date: 2024-12-30

-- Drop compression policy if exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.compression_settings
        WHERE hypertable_name = 'external_reddit_activity_raw'
    ) THEN
        PERFORM remove_compression_policy('external_reddit_activity_raw');
    END IF;
END $$;

-- Drop retention policy if exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE hypertable_name = 'external_reddit_activity_raw'
    ) THEN
        PERFORM remove_retention_policy('external_reddit_activity_raw');
    END IF;
END $$;

-- Drop indexes
DROP INDEX IF EXISTS idx_external_reddit_trace_unique;
DROP INDEX IF EXISTS idx_external_reddit_subreddit;

-- Drop the Reddit activity table
DROP TABLE IF EXISTS external_reddit_activity_raw CASCADE;

-- Remove any Reddit-related entries from other tables if they exist
-- (None found in current schema)

COMMENT ON SCHEMA public IS 'Reddit processing components removed - migration 027';