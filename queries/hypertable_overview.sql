-- Simple hypertable overview - just the basic info
SELECT 
    h.schema_name,
    h.table_name,
    h.num_dimensions,
    count(c.id) AS num_chunks,
    pg_size_pretty(pg_total_relation_size(format('%I.%I', h.schema_name, h.table_name)::regclass)) AS total_size
FROM _timescaledb_catalog.hypertable h
LEFT JOIN _timescaledb_catalog.chunk c ON h.id = c.hypertable_id
GROUP BY h.schema_name, h.table_name, h.num_dimensions
ORDER BY pg_total_relation_size(format('%I.%I', h.schema_name, h.table_name)::regclass) DESC;