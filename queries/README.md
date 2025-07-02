# Loom v2 Database Queries

This folder contains useful SQL queries for analyzing and monitoring the Loom v2 TimescaleDB database.

## Query Files

### 📊 `table_row_counts.sql`
Comprehensive query that shows row counts for all tables including:
- Differentiates between hypertables, chunks, and regular tables
- Shows table sizes and chunk counts
- Provides summary statistics
- Uses dynamic SQL for accurate counts

**Usage:**
```bash
make db-connect
\i queries/table_row_counts.sql
```

### 🚀 `table_row_counts_simple.sql`
Quick approximate row counts using PostgreSQL statistics:
- Faster execution (uses pg_stat_user_tables)
- Shows last vacuum/analyze times
- Good for quick checks
- Includes examples for exact counts

**Usage:**
```bash
make db-connect
\i queries/table_row_counts_simple.sql
```

### 📈 `hypertable_analytics.sql`
Detailed TimescaleDB hypertable analysis:
- Chunk distribution and sizes
- Data time spans and ingestion rates
- Compression statistics
- Average chunk sizes

**Usage:**
```bash
make db-connect
\i queries/hypertable_analytics.sql
```

### 🔄 `recent_data_check.sql`
Monitor recent data ingestion:
- Shows records from last hour
- Status indicators (✅ Active, ⚠️ Slow, ❌ Stale)
- Active device summary
- Time since last record

**Usage:**
```bash
make db-connect
\i queries/recent_data_check.sql
```

## Quick Commands

### Connect to database and run a query:
```bash
# Using make
make db-connect

# Direct psql
psql postgresql://loom:loom@localhost:5432/loom

# Run a specific query
\i queries/table_row_counts.sql

# Or pipe directly
psql postgresql://loom:loom@localhost:5432/loom < queries/recent_data_check.sql
```

### One-liner to check row counts:
```bash
psql postgresql://loom:loom@localhost:5432/loom -f queries/table_row_counts_simple.sql
```

### Watch recent data (refresh every 5 seconds):
```bash
watch -n 5 'psql postgresql://loom:loom@localhost:5432/loom -f queries/recent_data_check.sql'
```

## Common TimescaleDB Commands

```sql
-- List all hypertables
SELECT * FROM timescaledb_information.hypertables;

-- Show chunk interval for a hypertable
SELECT h.table_name, d.interval_length 
FROM _timescaledb_catalog.hypertable h
JOIN _timescaledb_catalog.dimension d ON h.id = d.hypertable_id;

-- Show compression status
SELECT hypertable_name, 
       chunk_name,
       before_compression_total_bytes,
       after_compression_total_bytes,
       compression_ratio
FROM timescaledb_information.compressed_chunk_stats
ORDER BY compression_ratio DESC;

-- Drop old chunks (careful!)
SELECT drop_chunks('device_audio_raw', older_than => interval '30 days');
```

## Tips

1. **Performance**: The comprehensive queries use dynamic SQL which can be slow on large databases. Use the simple version for quick checks.

2. **Hypertables**: TimescaleDB automatically partitions data into chunks. Individual chunks appear in `_timescaledb_internal` schema.

3. **Approximate vs Exact**: PostgreSQL's `n_live_tup` provides fast approximate counts. For exact counts, use `COUNT(*)` but it's slower.

4. **Time-based queries**: Always use time constraints when querying hypertables to leverage chunk exclusion.

5. **Monitoring**: Set up the `recent_data_check.sql` as a scheduled job to monitor data flow.