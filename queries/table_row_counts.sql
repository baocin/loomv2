-- Get row counts for all tables in the Loom TimescaleDB database
-- This query dynamically generates counts for all tables including hypertables
-- and provides useful metadata about table types and sizes

WITH table_counts AS (
    SELECT 
        schemaname,
        tablename,
        schemaname || '.' || tablename AS full_table_name,
        -- Check if it's a hypertable
        CASE 
            WHEN EXISTS (
                SELECT 1 FROM _timescaledb_catalog.hypertable h
                WHERE h.schema_name = t.schemaname 
                AND h.table_name = t.tablename
            ) THEN 'hypertable'
            WHEN schemaname = '_timescaledb_internal' THEN 'chunk'
            WHEN schemaname = 'public' THEN 'regular'
            ELSE 'system'
        END AS table_type,
        -- Get row count dynamically
        (xpath('/row/cnt/text()', 
            query_to_xml(format('SELECT count(*) AS cnt FROM %I.%I', schemaname, tablename), 
            false, true, '')))[1]::text::bigint AS row_count
    FROM pg_tables t
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    AND schemaname NOT LIKE 'pg_toast%'
    AND schemaname NOT LIKE '_timescaledb_cache%'
    AND schemaname NOT LIKE '_timescaledb_config%'
    -- Exclude internal TimescaleDB tables that are not chunks
    AND NOT (schemaname = '_timescaledb_internal' AND tablename NOT LIKE '_hyper_%')
),
hypertable_info AS (
    SELECT 
        h.schema_name,
        h.table_name,
        h.schema_name || '.' || h.table_name AS full_table_name,
        count(DISTINCT c.chunk_name) AS chunk_count,
        pg_size_pretty(sum(pg_relation_size(format('%I.%I', c.chunk_schema, c.chunk_name)::regclass))) AS total_size
    FROM _timescaledb_catalog.hypertable h
    LEFT JOIN _timescaledb_catalog.chunk c ON h.id = c.hypertable_id
    GROUP BY h.schema_name, h.table_name
)
SELECT 
    tc.schemaname AS schema,
    tc.tablename AS table_name,
    tc.table_type,
    TO_CHAR(tc.row_count, 'FM999,999,999,999') AS row_count,
    COALESCE(hi.chunk_count, 0) AS chunks,
    CASE 
        WHEN tc.table_type = 'hypertable' THEN COALESCE(hi.total_size, '0 bytes')
        ELSE pg_size_pretty(pg_relation_size(tc.full_table_name::regclass))
    END AS table_size,
    CASE 
        WHEN tc.table_type = 'hypertable' THEN 
            'Hypertable with ' || COALESCE(hi.chunk_count, 0) || ' chunks'
        WHEN tc.table_type = 'chunk' THEN 
            'TimescaleDB chunk'
        WHEN tc.tablename LIKE '%_raw' THEN 
            'Raw data table'
        WHEN tc.tablename LIKE '%_processed' THEN 
            'Processed data table'
        WHEN tc.tablename LIKE '%_analysis' THEN 
            'Analysis results table'
        ELSE 'Regular table'
    END AS description
FROM table_counts tc
LEFT JOIN hypertable_info hi ON tc.full_table_name = hi.full_table_name
WHERE tc.table_type != 'chunk'  -- Don't show individual chunks
ORDER BY 
    tc.table_type DESC,
    tc.row_count DESC,
    tc.schemaname,
    tc.tablename;

-- Summary statistics
SELECT 
    '=== SUMMARY ===' AS info
UNION ALL
SELECT 
    'Total tables: ' || count(DISTINCT tablename) || 
    ' (Hypertables: ' || count(DISTINCT CASE WHEN table_type = 'hypertable' THEN tablename END) || 
    ', Regular: ' || count(DISTINCT CASE WHEN table_type = 'regular' THEN tablename END) || ')'
FROM table_counts
WHERE table_type != 'chunk'
UNION ALL
SELECT 
    'Total rows across all tables: ' || TO_CHAR(sum(row_count), 'FM999,999,999,999')
FROM table_counts
WHERE table_type != 'chunk'
UNION ALL
SELECT 
    'Total chunks: ' || count(*)
FROM table_counts
WHERE table_type = 'chunk';