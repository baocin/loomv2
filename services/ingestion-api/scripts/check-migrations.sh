#!/bin/bash
# Script to check migration status for Loom v2

set -e

# Load environment variables
export DATABASE_URL="${DATABASE_URL:-postgresql://loom:loom@localhost:5432/loom}"

echo "Checking migration status..."
echo "Database URL: ${DATABASE_URL}"
echo ""

# Check if migrations table exists
if psql -t "${DATABASE_URL}" -c "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'schema_migrations');" | grep -q 't'; then
    echo "Applied migrations:"
    psql "${DATABASE_URL}" -c "SELECT version, applied_at FROM schema_migrations ORDER BY version;"
    
    echo ""
    echo "Latest migration:"
    psql "${DATABASE_URL}" -c "SELECT version, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 1;"
else
    echo "No migrations table found. Run ./scripts/run-migrations.sh to initialize."
fi

echo ""
echo "Georegion tables status:"
psql "${DATABASE_URL}" -c "
SELECT 
    table_name,
    CASE 
        WHEN table_name IS NOT NULL THEN 'EXISTS'
        ELSE 'NOT FOUND'
    END as status
FROM (
    VALUES 
        ('georegions'),
        ('location_georegion_detected'),
        ('location_address_geocoded')
) AS required_tables(table_name)
LEFT JOIN information_schema.tables 
    ON required_tables.table_name = information_schema.tables.table_name 
    AND table_schema = 'public'
ORDER BY required_tables.table_name;
"

echo ""
echo "Current georegions:"
if psql -t "${DATABASE_URL}" -c "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'georegions');" | grep -q 't'; then
    psql "${DATABASE_URL}" -c "SELECT id, name, type, is_active, radius_meters FROM georegions ORDER BY type, name;"
else
    echo "Georegions table does not exist yet."
fi