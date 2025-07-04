-- Migration: Optimize Kafka topic partitions for high-volume data streams
-- This migration updates partition counts for topics based on their expected throughput
-- and processing complexity to improve parallelism and reduce consumer lag

-- Create a function to safely update topic partitions
-- Note: In production, increasing partitions requires Kafka admin operations
-- This table stores the desired configuration that should be applied
CREATE TABLE IF NOT EXISTS topic_partition_changes (
    id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL REFERENCES kafka_topics(topic_name),
    current_partitions INTEGER NOT NULL,
    target_partitions INTEGER NOT NULL,
    reason TEXT NOT NULL,
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_partition_increase CHECK (target_partitions > current_partitions)
);

-- Record partition optimization recommendations
INSERT INTO topic_partition_changes (topic_name, current_partitions, target_partitions, reason)
SELECT
    kt.topic_name,
    kt.partitions as current_partitions,
    CASE
        -- High-volume sensor data needs more partitions
        WHEN kt.topic_name = 'device.sensor.accelerometer.raw' THEN 10
        WHEN kt.topic_name = 'device.sensor.accelerometer.windowed' THEN 10

        -- Audio processing pipeline
        WHEN kt.topic_name = 'device.audio.raw' THEN 6
        WHEN kt.topic_name = 'media.audio.vad_filtered' THEN 6
        WHEN kt.topic_name = 'media.text.transcribed.words' THEN 6

        -- Vision pipeline topics
        WHEN kt.topic_name IN ('device.image.camera.raw', 'device.video.screen.raw') THEN 4
        WHEN kt.topic_name LIKE 'media.image.%' THEN 4

        -- App lifecycle events (moderate volume)
        WHEN kt.topic_name IN ('os.events.app_lifecycle.raw', 'os.events.system.raw') THEN 4

        -- Motion classification pipeline
        WHEN kt.topic_name LIKE 'motion.%' THEN 6

        -- External data ingestion (can be parallelized)
        WHEN kt.topic_name = 'task.url.ingest' THEN 6

        -- Default to current for others
        ELSE kt.partitions
    END as target_partitions,
    CASE
        WHEN kt.topic_name LIKE '%accelerometer%' THEN 'High-volume sensor data (50 events/sec) requires more parallelism'
        WHEN kt.topic_name LIKE '%audio%' THEN 'Audio pipeline processes 10 events/sec with complex STT processing'
        WHEN kt.topic_name LIKE '%image%' OR kt.topic_name LIKE '%video%' THEN 'Vision processing is compute-intensive and benefits from parallelism'
        WHEN kt.topic_name LIKE '%app_lifecycle%' OR kt.topic_name LIKE '%system%' THEN 'Moderate volume OS events (2 events/sec) with multiple consumers'
        WHEN kt.topic_name LIKE 'motion.%' THEN 'Motion classification handles 50 events/sec with multiple stages'
        WHEN kt.topic_name = 'task.url.ingest' THEN 'URL ingestion can be parallelized across multiple workers'
        ELSE 'Current partition count is adequate'
    END as reason
FROM kafka_topics kt
WHERE kt.is_active = true
  AND kt.partitions < CASE
        WHEN kt.topic_name = 'device.sensor.accelerometer.raw' THEN 10
        WHEN kt.topic_name = 'device.sensor.accelerometer.windowed' THEN 10
        WHEN kt.topic_name = 'device.audio.raw' THEN 6
        WHEN kt.topic_name = 'media.audio.vad_filtered' THEN 6
        WHEN kt.topic_name = 'media.text.transcribed.words' THEN 6
        WHEN kt.topic_name IN ('device.image.camera.raw', 'device.video.screen.raw') THEN 4
        WHEN kt.topic_name LIKE 'media.image.%' THEN 4
        WHEN kt.topic_name IN ('os.events.app_lifecycle.raw', 'os.events.system.raw') THEN 4
        WHEN kt.topic_name LIKE 'motion.%' THEN 6
        WHEN kt.topic_name = 'task.url.ingest' THEN 6
        ELSE kt.partitions
    END;

-- Update the kafka_topics table with recommended partitions
-- Note: This only updates the database config. Actual Kafka changes need to be applied separately
UPDATE kafka_topics kt
SET
    partitions = tpc.target_partitions,
    updated_at = NOW()
FROM topic_partition_changes tpc
WHERE kt.topic_name = tpc.topic_name
  AND tpc.applied = false;

-- Create a view to monitor partition efficiency
CREATE OR REPLACE VIEW v_partition_efficiency AS
WITH topic_load AS (
    SELECT
        kt.topic_name,
        kt.partitions,
        kt.category,
        pf.flow_name,
        pf.priority,
        pf.expected_events_per_second,
        COUNT(DISTINCT ps.service_name) as consumer_services,
        SUM(ps.replicas) as total_consumer_replicas
    FROM kafka_topics kt
    LEFT JOIN pipeline_stage_topics pst ON kt.topic_name = pst.topic_name AND pst.topic_role = 'input'
    LEFT JOIN pipeline_stages ps ON pst.stage_id = ps.id
    LEFT JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
    WHERE kt.is_active = true
    GROUP BY kt.topic_name, kt.partitions, kt.category, pf.flow_name, pf.priority, pf.expected_events_per_second
)
SELECT
    topic_name,
    category,
    partitions,
    flow_name,
    priority,
    expected_events_per_second,
    consumer_services,
    total_consumer_replicas,
    -- Calculate events per partition
    CASE
        WHEN expected_events_per_second IS NOT NULL AND partitions > 0
        THEN expected_events_per_second / partitions::numeric
        ELSE NULL
    END as events_per_partition_per_sec,
    -- Recommend if more partitions needed
    CASE
        WHEN expected_events_per_second IS NOT NULL AND partitions > 0
            AND (expected_events_per_second / partitions::numeric) > 10
        THEN 'Consider increasing partitions'
        WHEN total_consumer_replicas > partitions * 2
        THEN 'More consumers than partitions - consider increasing partitions'
        ELSE 'Partition count appears adequate'
    END as recommendation,
    -- Calculate ideal partition count
    CASE
        WHEN expected_events_per_second IS NOT NULL
        THEN GREATEST(
            CEIL(expected_events_per_second / 10.0), -- Target ~10 events/partition/sec
            total_consumer_replicas, -- At least as many partitions as consumer replicas
            3 -- Minimum 3 partitions for redundancy
        )::integer
        ELSE partitions
    END as recommended_partitions
FROM topic_load
ORDER BY
    CASE priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
        ELSE 5
    END,
    expected_events_per_second DESC NULLS LAST;

-- Create an admin script to apply partition changes
CREATE OR REPLACE FUNCTION generate_partition_update_script()
RETURNS TABLE(script_line TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 'echo "Updating partitions for topic: ' || topic_name || ' from ' || current_partitions || ' to ' || target_partitions || '"'
    FROM topic_partition_changes
    WHERE applied = false
    UNION ALL
    SELECT 'kafka-topics.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS --alter --topic ' || topic_name || ' --partitions ' || target_partitions
    FROM topic_partition_changes
    WHERE applied = false
    ORDER BY 1;
END;
$$ LANGUAGE plpgsql;

-- Add helper function to mark partition changes as applied
CREATE OR REPLACE FUNCTION mark_partition_changes_applied(p_topic_name TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE topic_partition_changes
    SET applied = true, applied_at = NOW()
    WHERE topic_name = p_topic_name AND applied = false;
END;
$$ LANGUAGE plpgsql;

-- Create monitoring view for consumer lag by partition
CREATE OR REPLACE VIEW v_partition_distribution_monitor AS
SELECT
    kt.topic_name,
    kt.partitions,
    ps.service_name,
    ps.replicas as service_replicas,
    pcc.consumer_group_id,
    pcc.partition_assignment_strategy,
    -- Calculate optimal partition assignment
    CASE
        WHEN pcc.partition_assignment_strategy = 'sticky'
        THEN 'Partitions stick to consumers for cache efficiency'
        WHEN pcc.partition_assignment_strategy = 'range'
        THEN 'Partitions assigned in contiguous ranges'
        WHEN pcc.partition_assignment_strategy = 'roundrobin'
        THEN 'Partitions distributed round-robin'
        ELSE 'Cooperative rebalancing for minimal disruption'
    END as assignment_behavior,
    -- Partition to replica ratio
    CASE
        WHEN ps.replicas > 0
        THEN ROUND((kt.partitions::numeric / ps.replicas), 2)
        ELSE NULL
    END as partitions_per_replica,
    -- Recommendation
    CASE
        WHEN ps.replicas > kt.partitions
        THEN 'WARNING: More replicas than partitions - some consumers will be idle'
        WHEN kt.partitions > ps.replicas * 10
        THEN 'WARNING: Too many partitions per replica - may cause rebalancing issues'
        ELSE 'OK'
    END as distribution_status
FROM kafka_topics kt
JOIN pipeline_stage_topics pst ON kt.topic_name = pst.topic_name AND pst.topic_role = 'input'
JOIN pipeline_stages ps ON pst.stage_id = ps.id
LEFT JOIN pipeline_consumer_configs pcc ON ps.service_name = pcc.service_name
WHERE kt.is_active = true
ORDER BY kt.topic_name, ps.service_name;

-- Add comments
COMMENT ON TABLE topic_partition_changes IS 'Tracks recommended partition count changes for Kafka topics';
COMMENT ON VIEW v_partition_efficiency IS 'Monitors partition efficiency and recommends optimal partition counts';
COMMENT ON VIEW v_partition_distribution_monitor IS 'Monitors how partitions are distributed across consumer replicas';
COMMENT ON FUNCTION generate_partition_update_script() IS 'Generates shell script to apply partition changes to Kafka';

-- Output summary of recommended changes
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM topic_partition_changes WHERE applied = false;
    IF v_count > 0 THEN
        RAISE NOTICE 'Created % partition optimization recommendations. Run SELECT * FROM generate_partition_update_script(); to get the update script.', v_count;
    ELSE
        RAISE NOTICE 'No partition optimizations needed at this time.';
    END IF;
END;
$$;
