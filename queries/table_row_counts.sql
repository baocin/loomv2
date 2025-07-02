-- Get row counts for all tables in the Loom TimescaleDB database
-- This query provides a simpler approach that works with standard PostgreSQL

-- First, let's check if TimescaleDB is installed
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        RAISE NOTICE 'TimescaleDB extension not found. Showing standard PostgreSQL stats.';
    END IF;
END $$;

-- Table row counts and sizes
SELECT 
    n.nspname AS schema,
    c.relname AS table_name,
    CASE 
        WHEN n.nspname = '_timescaledb_internal' AND c.relname LIKE '_hyper_%' THEN 'chunk'
        WHEN EXISTS (
            SELECT 1 FROM pg_extension e 
            WHERE e.extname = 'timescaledb'
            AND EXISTS (
                SELECT 1 FROM _timescaledb_catalog.hypertable h 
                WHERE h.schema_name = n.nspname 
                AND h.table_name = c.relname
            )
        ) THEN 'hypertable'
        WHEN n.nspname = 'public' THEN 'regular'
        ELSE 'system'
    END AS table_type,
    c.reltuples::bigint AS row_count_estimate,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
    CASE 
        WHEN c.relname LIKE '%_raw' THEN 'Raw data table'
        WHEN c.relname LIKE '%_processed' THEN 'Processed data table'
        WHEN c.relname LIKE '%_analysis' THEN 'Analysis results table'
        WHEN c.relname LIKE 'device_%' THEN 'Device data table'
        WHEN c.relname LIKE 'media_%' THEN 'Media processing table'
        WHEN c.relname LIKE 'external_%' THEN 'External data table'
        ELSE 'Other table'
    END AS category
FROM pg_class c
LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p')  -- regular tables and partitioned tables
    AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    AND n.nspname NOT LIKE 'pg_toast%'
    AND n.nspname NOT LIKE '_timescaledb_cache%'
    AND n.nspname NOT LIKE '_timescaledb_config%'
    AND NOT (n.nspname = '_timescaledb_internal' AND c.relname NOT LIKE '_hyper_%')
ORDER BY 
    CASE 
        WHEN n.nspname = 'public' THEN 1
        WHEN n.nspname = '_timescaledb_internal' THEN 2
        ELSE 3
    END,
    c.reltuples DESC,
    c.relname;

-- Summary by schema
SELECT 
    '=== SUMMARY BY SCHEMA ===' AS info;

SELECT 
    n.nspname AS schema,
    count(*) AS table_count,
    TO_CHAR(sum(c.reltuples), 'FM999,999,999,999') AS total_rows_estimate,
    pg_size_pretty(sum(pg_total_relation_size(c.oid))) AS total_size
FROM pg_class c
LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p')
    AND n.nspname NOT IN ('pg_catalog', 'information_schema')
    AND n.nspname NOT LIKE 'pg_toast%'
GROUP BY n.nspname
ORDER BY sum(c.reltuples) DESC;

-- Hypertable information (if TimescaleDB is installed)
SELECT 
    '=== HYPERTABLE INFORMATION ===' AS info
WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb');

SELECT 
    h.schema_name,
    h.table_name,
    h.num_dimensions,
    d.column_name AS time_column,
    d.interval_length AS chunk_interval,
    count(DISTINCT c.chunk_name) AS chunk_count
FROM _timescaledb_catalog.hypertable h
JOIN _timescaledb_catalog.dimension d ON h.id = d.hypertable_id
LEFT JOIN _timescaledb_catalog.chunk c ON h.id = c.hypertable_id
WHERE EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')
GROUP BY h.schema_name, h.table_name, h.num_dimensions, d.column_name, d.interval_length
ORDER BY h.schema_name, h.table_name;