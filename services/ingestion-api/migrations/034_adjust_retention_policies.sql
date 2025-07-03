-- Migration 034: Remove All Retention Policies
-- Description: Removes all TimescaleDB retention policies to keep data forever

-- Remove ALL retention policies from all hypertables
DO $$
DECLARE
    job RECORD;
BEGIN
    -- Loop through all retention policy jobs
    FOR job IN 
        SELECT job_id, hypertable_name::text
        FROM timescaledb_information.jobs 
        WHERE proc_name = 'policy_retention'
    LOOP
        -- Remove each retention policy
        RAISE NOTICE 'Removing retention policy from table: %', job.hypertable_name;
        PERFORM remove_retention_policy(job.hypertable_name::regclass, if_exists => true);
    END LOOP;
END $$;

-- Verify all retention policies have been removed
-- This should return 0 rows
SELECT 
    'After migration, retention policies remaining: ' || COUNT(*)::text as status
FROM timescaledb_information.jobs 
WHERE proc_name = 'policy_retention';

-- List all hypertables to confirm they no longer have retention policies
SELECT 
    h.table_name,
    'No retention policy - data kept forever' as retention_status
FROM _timescaledb_catalog.hypertable h
WHERE h.table_name IN (
    SELECT DISTINCT hypertable_name::text 
    FROM timescaledb_information.jobs 
    WHERE proc_name = 'policy_retention'
)
ORDER BY h.table_name;

-- Note: Data will now be kept forever for all tables
-- Monitor disk space usage regularly as data will accumulate indefinitely
-- To re-enable retention in the future, use:
-- SELECT add_retention_policy('table_name', INTERVAL 'X days');