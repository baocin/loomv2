#!/bin/bash
# Script to run database migrations for Loom v2

set -e

# Load environment variables
export DATABASE_URL="${DATABASE_URL:-postgresql://loom:loom@localhost:5432/loom}"

echo "Running database migrations..."
echo "Database URL: ${DATABASE_URL}"

# Create migrations tracking table if it doesn't exist
psql "${DATABASE_URL}" <<EOF
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
EOF

# Get list of applied migrations
APPLIED_MIGRATIONS=$(psql -t -A "${DATABASE_URL}" -c "SELECT version FROM schema_migrations ORDER BY version;")

# Directory containing migration files
MIGRATIONS_DIR="$(dirname "$0")/../migrations"

# Run each migration in order
for migration_file in $(ls -1 "${MIGRATIONS_DIR}"/*.sql | sort -V); do
    migration_name=$(basename "${migration_file}")
    migration_version="${migration_name%%.sql}"
    
    # Check if migration has already been applied
    if echo "${APPLIED_MIGRATIONS}" | grep -q "^${migration_version}$"; then
        echo "Skipping ${migration_name} (already applied)"
    else
        echo "Applying ${migration_name}..."
        
        # Run the migration
        psql "${DATABASE_URL}" < "${migration_file}"
        
        # Record that the migration has been applied
        psql "${DATABASE_URL}" -c "INSERT INTO schema_migrations (version) VALUES ('${migration_version}');"
        
        echo "Applied ${migration_name} successfully"
    fi
done

echo "All migrations completed successfully!"

# Show current schema version
echo ""
echo "Current schema version:"
psql "${DATABASE_URL}" -c "SELECT version, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 1;"