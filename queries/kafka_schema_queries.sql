-- Example queries for the Kafka schema management system

-- 1. List all active topics with their retention policies
SELECT 
    topic_name,
    category,
    source,
    datatype,
    description,
    retention_days,
    partitions,
    compression_type
FROM kafka_topics
WHERE is_active = true
ORDER BY category, source, datatype;

-- 2. Find all topics related to audio processing
SELECT 
    topic_name,
    description,
    retention_days
FROM kafka_topics
WHERE topic_name LIKE '%audio%'
   OR topic_name LIKE '%speech%'
   OR topic_name LIKE '%vad%'
ORDER BY topic_name;

-- 3. Show the complete audio processing pipeline
SELECT * FROM v_pipeline_overview
WHERE flow_name = 'audio_processing'
ORDER BY stage_order;

-- 4. Find what topics a specific service consumes and produces
SELECT 
    ps.service_name,
    ps.stage_name,
    array_agg(DISTINCT pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as consumes,
    array_agg(DISTINCT pst.topic_name) FILTER (WHERE pst.topic_role = 'output') as produces
FROM pipeline_stages ps
JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
WHERE ps.service_name = 'kyutai-stt'
GROUP BY ps.service_name, ps.stage_name;

-- 5. Show data lineage - trace how data flows from device.audio.raw
WITH RECURSIVE topic_flow AS (
    -- Start with device.audio.raw
    SELECT 
        'device.audio.raw'::text as source_topic,
        'device.audio.raw'::text as target_topic,
        0 as depth,
        ARRAY['device.audio.raw']::text[] as path
    
    UNION ALL
    
    -- Recursively find all downstream topics
    SELECT 
        tf.source_topic,
        td.target_topic,
        tf.depth + 1,
        tf.path || td.target_topic
    FROM topic_flow tf
    JOIN v_topic_dependencies td ON tf.target_topic = td.source_topic
    WHERE tf.depth < 5  -- Limit recursion depth
      AND NOT td.target_topic = ANY(tf.path)  -- Prevent cycles
)
SELECT DISTINCT
    depth,
    source_topic,
    target_topic,
    path
FROM topic_flow
WHERE depth > 0
ORDER BY depth, target_topic;

-- 6. Get the current schema for a topic
SELECT get_topic_schema('device.audio.raw');

-- 7. Get complete pipeline configuration as JSON
SELECT get_pipeline_config('audio_processing');

-- 8. Find all topics that don't have schemas defined
SELECT 
    kt.topic_name,
    kt.description
FROM kafka_topics kt
LEFT JOIN kafka_topic_schemas kts ON kt.topic_name = kts.topic_name
WHERE kts.id IS NULL
  AND kt.is_active = true
ORDER BY kt.topic_name;

-- 9. Show field mappings for WiFi topic (kafka-to-db consumer)
SELECT 
    source_field_path,
    target_column,
    data_type,
    transformation,
    is_required
FROM topic_field_mappings
WHERE topic_name = 'device.network.wifi.raw'
ORDER BY is_required DESC, target_column;

-- 10. Find topics with the most complex processing pipelines
SELECT 
    pst_in.topic_name as input_topic,
    COUNT(DISTINCT ps.id) as processing_stages,
    COUNT(DISTINCT pst_out.topic_name) as output_topics,
    array_agg(DISTINCT ps.service_name) as services
FROM pipeline_stage_topics pst_in
JOIN pipeline_stages ps ON pst_in.stage_id = ps.id
JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
WHERE pst_in.topic_role = 'input'
GROUP BY pst_in.topic_name
HAVING COUNT(DISTINCT ps.id) > 1
ORDER BY processing_stages DESC;

-- 11. Validate all topic names follow naming convention
SELECT 
    topic_name,
    validate_topic_name(topic_name) as is_valid,
    CASE 
        WHEN NOT validate_topic_name(topic_name) THEN 'Invalid naming convention'
        ELSE 'Valid'
    END as validation_result
FROM kafka_topics
WHERE NOT validate_topic_name(topic_name);

-- 12. Show topics grouped by retention policy
SELECT 
    retention_days,
    COUNT(*) as topic_count,
    array_agg(topic_name ORDER BY topic_name) as topics
FROM kafka_topics
WHERE is_active = true
GROUP BY retention_days
ORDER BY retention_days;

-- 13. Find services that might need scaling based on data volume
SELECT 
    ps.service_name,
    ps.replicas as current_replicas,
    pf.expected_events_per_second,
    pf.average_event_size_bytes,
    (pf.expected_events_per_second * pf.average_event_size_bytes / 1024.0 / 1024.0)::numeric(10,2) as mb_per_second,
    CASE 
        WHEN pf.expected_events_per_second > 100 AND ps.replicas < 3 THEN 'Consider scaling up'
        WHEN pf.expected_events_per_second < 10 AND ps.replicas > 1 THEN 'Consider scaling down'
        ELSE 'OK'
    END as scaling_recommendation
FROM pipeline_stages ps
JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
WHERE pf.expected_events_per_second IS NOT NULL
ORDER BY mb_per_second DESC;

-- 14. Export all topic configurations as JSON for documentation
SELECT jsonb_pretty(
    jsonb_build_object(
        'topics', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', topic_name,
                    'category', category,
                    'source', source,
                    'datatype', datatype,
                    'stage', stage,
                    'description', description,
                    'retention_days', retention_days,
                    'schema_version', (
                        SELECT version 
                        FROM kafka_topic_schemas 
                        WHERE topic_name = kt.topic_name 
                        AND is_current = true
                    )
                ) ORDER BY topic_name
            )
            FROM kafka_topics kt
            WHERE is_active = true
        )
    )
);