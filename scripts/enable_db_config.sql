-- Enable database-driven configuration by updating the topic validation function
-- This fixes the issue where some valid topic names were being rejected

UPDATE pipeline_stages SET 
    configuration = jsonb_set(
        COALESCE(configuration, '{}'),
        '{use_database_config}',
        'true',
        true
    )
WHERE service_name IN ('kafka-to-db-consumer', 'generic-kafka-to-db-consumer');

-- Show current configuration
SELECT 
    'Updated kafka-to-db consumer configuration' as action,
    COUNT(*) as affected_stages
FROM pipeline_stages 
WHERE service_name IN ('kafka-to-db-consumer', 'generic-kafka-to-db-consumer');