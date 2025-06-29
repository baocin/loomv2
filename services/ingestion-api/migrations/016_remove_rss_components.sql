-- Migration 016: Remove RSS Components
-- Description: Removes RSS-related table, indexes, and policies from the database

-- Remove compression and retention policies for RSS table (if they exist)
-- Check if table exists before trying to remove policies
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = 'external_rss_items_raw') THEN
        PERFORM remove_compression_policy('external_rss_items_raw', true);
        PERFORM remove_retention_policy('external_rss_items_raw', true);
    END IF;
END $$;

-- Drop indexes related to RSS table
DROP INDEX IF EXISTS idx_external_rss_feed;

-- Drop the RSS table
DROP TABLE IF EXISTS external_rss_items_raw;

-- Remove any references to RSS from the hypertables view
-- (This is informational - the table removal above handles the actual cleanup)
SELECT
    'RSS table and related components removed successfully' as status,
    COUNT(*) as remaining_external_tables
FROM timescaledb_information.hypertables h
WHERE hypertable_name LIKE 'external_%' AND hypertable_name != 'external_rss_items_raw';
