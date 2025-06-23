#!/bin/bash
# TimescaleDB Migration Runner

set -e

# Database connection parameters
DB_HOST="${LOOM_DB_HOST:-localhost}"
DB_PORT="${LOOM_DB_PORT:-5432}"
DB_NAME="${LOOM_DB_NAME:-loom}"
DB_USER="${LOOM_DB_USER:-loom}"
DB_PASSWORD="${LOOM_DB_PASSWORD:-loom}"

export PGPASSWORD=$DB_PASSWORD

echo "🚀 Starting TimescaleDB migrations..."
echo "   Host: $DB_HOST:$DB_PORT"
echo "   Database: $DB_NAME"
echo ""

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
until psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c '\q' 2>/dev/null; do
    sleep 1
done
echo "✅ Database is ready!"

# Create migrations tracking table
echo "📋 Creating migrations table..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<EOF
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
EOF

# Run migrations
MIGRATION_DIR="$(dirname "$0")"
for migration in $(ls $MIGRATION_DIR/*.sql | sort); do
    filename=$(basename $migration)
    
    # Check if migration was already executed
    executed=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM schema_migrations WHERE filename = '$filename'")
    
    if [ $executed -eq 0 ]; then
        echo "📝 Running migration: $filename"
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $migration
        
        # Record successful migration
        psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "INSERT INTO schema_migrations (filename) VALUES ('$filename')"
        echo "✅ Completed: $filename"
    else
        echo "⏭️  Skipping (already executed): $filename"
    fi
done

echo ""
echo "🎉 All migrations completed successfully!"

# Show database status
echo ""
echo "📊 Database Status:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<EOF
-- TimescaleDB version
SELECT extversion AS timescaledb_version FROM pg_extension WHERE extname = 'timescaledb';

-- List hypertables
SELECT hypertable_name, 
       num_chunks,
       compression_enabled,
       total_bytes / 1024 / 1024 AS total_mb,
       compressed_bytes / 1024 / 1024 AS compressed_mb
FROM timescaledb_information.hypertables;

-- Active jobs
SELECT job_id, proc_name, schedule_interval, next_start 
FROM timescaledb_information.jobs 
WHERE proc_name IN ('policy_retention', 'policy_compression')
ORDER BY job_id;
EOF