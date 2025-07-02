-- Show chunk details for hypertables
SELECT 
    ht.schema_name || '.' || ht.table_name AS hypertable,
    ch.schema_name || '.' || ch.table_name AS chunk_name,
    pg_size_pretty(pg_relation_size(format('%I.%I', ch.schema_name, ch.table_name)::regclass)) AS chunk_size,
    ch.creation_time,
    CASE 
        WHEN ch.compressed_chunk_id IS NOT NULL THEN 'Compressed'
        ELSE 'Uncompressed'
    END AS compression_status
FROM _timescaledb_catalog.hypertable ht
JOIN _timescaledb_catalog.chunk ch ON ht.id = ch.hypertable_id
WHERE NOT ch.dropped
ORDER BY ht.table_name, ch.creation_time DESC
LIMIT 50;