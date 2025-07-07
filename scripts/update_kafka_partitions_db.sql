-- Script to update Kafka topic partitions in database to match single partition configuration
-- This updates the kafka_topics table to reflect the actual Kafka configuration

-- Start transaction
BEGIN;

-- Update all active topics to have 1 partition
UPDATE kafka_topics
SET 
    partitions = 1,
    updated_at = NOW()
WHERE is_active = true
  AND partitions != 1;

-- Show what was updated
SELECT 
    topic_name,
    partitions,
    category,
    retention_days,
    updated_at
FROM kafka_topics
WHERE is_active = true
ORDER BY category, topic_name;

-- Log the change in topic_partition_changes table if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'topic_partition_changes') THEN
        
        -- Mark all previous changes as applied
        UPDATE topic_partition_changes
        SET applied = true,
            applied_at = NOW()
        WHERE applied = false;
        
        -- Insert record of this change
        INSERT INTO topic_partition_changes (
            topic_name, 
            current_partitions, 
            target_partitions, 
            reason, 
            applied, 
            applied_at
        )
        SELECT 
            topic_name,
            partitions,
            1,
            'Debug mode: Reset all topics to single partition for troubleshooting',
            true,
            NOW()
        FROM kafka_topics
        WHERE is_active = true
          AND topic_name NOT IN (
              SELECT topic_name 
              FROM topic_partition_changes 
              WHERE target_partitions = 1 
                AND reason LIKE 'Debug mode%'
          );
    END IF;
END $$;

-- Commit the changes
COMMIT;

-- Summary
SELECT 
    COUNT(*) as total_topics,
    SUM(CASE WHEN partitions = 1 THEN 1 ELSE 0 END) as single_partition_topics,
    SUM(CASE WHEN partitions > 1 THEN 1 ELSE 0 END) as multi_partition_topics
FROM kafka_topics
WHERE is_active = true;