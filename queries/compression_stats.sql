-- Compression statistics for hypertables
SELECT 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    count(ch.id) AS total_chunks,
    count(CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN 1 END) AS compressed_chunks,
    ROUND(100.0 * count(CASE WHEN ch.compressed_chunk_id IS NOT NULL THEN 1 END)::numeric / 
          NULLIF(count(ch.id), 0), 2) AS compression_rate_pct,
    pg_size_pretty(
        sum(pg_relation_size(format('%I.%I', ch.schema_name, ch.table_name)::regclass))
    ) AS total_chunk_size
FROM _timescaledb_catalog.hypertable ht
LEFT JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id AND NOT ch.dropped
GROUP BY ht.schema_name, ht.table_name
HAVING count(ch.id) > 0
ORDER BY compression_rate_pct DESC;