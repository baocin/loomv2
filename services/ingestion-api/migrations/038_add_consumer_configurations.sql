-- Migration: Add consumer configuration tables for optimized Kafka processing
-- This migration adds configuration storage for Kafka consumer groups to optimize
-- processing based on service characteristics and workload patterns

-- Create consumer configuration table
CREATE TABLE IF NOT EXISTS pipeline_consumer_configs (
    service_name TEXT PRIMARY KEY,
    consumer_group_id TEXT NOT NULL,
    max_poll_records INTEGER DEFAULT 100,
    session_timeout_ms INTEGER DEFAULT 60000,
    max_poll_interval_ms INTEGER DEFAULT 300000,
    heartbeat_interval_ms INTEGER DEFAULT 20000,
    partition_assignment_strategy TEXT DEFAULT 'range' CHECK (partition_assignment_strategy IN ('range', 'roundrobin', 'sticky', 'cooperative-sticky')),
    enable_auto_commit BOOLEAN DEFAULT false,
    auto_commit_interval_ms INTEGER DEFAULT 5000,
    auto_offset_reset TEXT DEFAULT 'earliest' CHECK (auto_offset_reset IN ('earliest', 'latest', 'none')),
    fetch_min_bytes INTEGER DEFAULT 1,
    fetch_max_wait_ms INTEGER DEFAULT 500,
    max_partition_fetch_bytes INTEGER DEFAULT 1048576, -- 1MB default
    request_timeout_ms INTEGER DEFAULT 305000,
    retry_backoff_ms INTEGER DEFAULT 100,
    reconnect_backoff_ms INTEGER DEFAULT 50,
    reconnect_backoff_max_ms INTEGER DEFAULT 1000,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_timeouts CHECK (
        session_timeout_ms > heartbeat_interval_ms * 2 AND
        max_poll_interval_ms > session_timeout_ms AND
        request_timeout_ms > max_poll_interval_ms
    ),
    CONSTRAINT valid_poll_records CHECK (max_poll_records > 0 AND max_poll_records <= 5000)
);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER update_pipeline_consumer_configs_updated_at
    BEFORE UPDATE ON pipeline_consumer_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add foreign key constraint to ensure service exists
ALTER TABLE pipeline_consumer_configs
    ADD CONSTRAINT fk_consumer_config_service
    FOREIGN KEY (service_name)
    REFERENCES pipeline_stages(service_name)
    ON DELETE CASCADE;

-- Create index for monitoring consumer lag by service
CREATE INDEX IF NOT EXISTS idx_consumer_lag_monitoring
    ON pipeline_stage_topics(topic_name, topic_role)
    WHERE topic_role = 'input';

-- Create index for consumer group lookups
CREATE INDEX IF NOT EXISTS idx_consumer_group_lookup
    ON pipeline_consumer_configs(consumer_group_id);

-- Insert optimized configurations for existing services based on their processing characteristics

-- Audio processing services (high volume, simple processing)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, partition_assignment_strategy
) VALUES
    -- VAD is fast, can process many records
    ('silero-vad', 'loom-vad-processor', 500, 30000, 60000, 10000, 'sticky'),
    -- Audio classifier is medium complexity
    ('audio-classifier', 'loom-audio-classifier', 200, 45000, 90000, 15000, 'sticky')
ON CONFLICT (service_name) DO NOTHING;

-- Speech-to-text services (complex, GPU-intensive)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, max_partition_fetch_bytes
) VALUES
    -- STT needs more time per record
    ('kyutai-stt', 'loom-kyutai-stt', 10, 120000, 300000, 40000, 10485760) -- 10MB for audio chunks
ON CONFLICT (service_name) DO NOTHING;

-- Vision processing services (very complex, GPU-intensive)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, max_partition_fetch_bytes
) VALUES
    -- Vision models process one image at a time
    ('moondream-processor', 'loom-moondream-vision', 1, 300000, 600000, 60000, 52428800), -- 50MB for images
    ('minicpm-vision', 'loom-minicpm-vision', 1, 300000, 600000, 60000, 52428800),
    ('face-detector', 'loom-face-detector', 5, 120000, 240000, 40000, 20971520), -- 20MB
    ('moondream-vision', 'loom-moondream-analyzer', 1, 300000, 600000, 60000, 52428800),
    ('vision-preprocessor', 'loom-vision-preprocessor', 10, 60000, 120000, 20000, 20971520)
ON CONFLICT (service_name) DO NOTHING;

-- OCR processing services (medium complexity)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms
) VALUES
    ('image-preprocessor', 'loom-image-preprocessor', 20, 60000, 120000, 20000),
    ('ocr-processor', 'loom-ocr-processor', 5, 90000, 180000, 30000),
    ('tesseract-ocr', 'loom-tesseract-ocr', 5, 90000, 180000, 30000),
    ('text-postprocessor', 'loom-text-postprocessor', 50, 30000, 60000, 10000)
ON CONFLICT (service_name) DO NOTHING;

-- Motion and sensor processing (high volume, simple)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, partition_assignment_strategy
) VALUES
    ('accelerometer-aggregator', 'loom-accel-aggregator', 1000, 30000, 60000, 10000, 'sticky'),
    ('motion-detector', 'loom-motion-detector', 500, 30000, 60000, 10000, 'sticky'),
    ('activity-classifier', 'loom-activity-classifier', 200, 45000, 90000, 15000, 'sticky')
ON CONFLICT (service_name) DO NOTHING;

-- Database writer services (batch processing)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, enable_auto_commit
) VALUES
    ('timescale-writer', 'loom-timescale-writer', 1000, 60000, 120000, 20000, true),
    ('kafka-to-db-saver', 'loom-kafka-to-db', 1000, 60000, 120000, 20000, true)
ON CONFLICT (service_name) DO NOTHING;

-- LLM and reasoning services (very complex, require long timeouts)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, request_timeout_ms
) VALUES
    ('mistral-reasoning', 'loom-mistral-reasoning', 1, 600000, 1200000, 120000, 1205000), -- 20 min timeout
    ('text-embedder', 'loom-text-embedder', 20, 120000, 240000, 40000, 245000)
ON CONFLICT (service_name) DO NOTHING;

-- External data processing services (network I/O bound)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, fetch_max_wait_ms
) VALUES
    ('email-fetcher', 'loom-email-fetcher', 10, 180000, 360000, 60000, 5000),
    ('calendar-fetcher', 'loom-calendar-fetcher', 10, 180000, 360000, 60000, 5000),
    ('hn-scraper', 'loom-hn-scraper', 5, 300000, 600000, 60000, 5000),
    ('content-fetcher', 'loom-content-fetcher', 5, 300000, 600000, 60000, 5000)
ON CONFLICT (service_name) DO NOTHING;

-- App lifecycle and monitoring services (medium volume, simple)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms
) VALUES
    ('app-lifecycle-processor', 'loom-app-lifecycle', 100, 30000, 60000, 10000),
    ('app-event-enricher', 'loom-app-enricher', 100, 30000, 60000, 10000),
    ('power-enricher', 'loom-power-enricher', 100, 30000, 60000, 10000),
    ('power-pattern-detector', 'loom-power-patterns', 50, 45000, 90000, 15000)
ON CONFLICT (service_name) DO NOTHING;

-- Location and geocoding services (network I/O, rate limited)
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, retry_backoff_ms
) VALUES
    ('gps-geocoding-consumer', 'loom-geocoder', 10, 120000, 240000, 40000, 1000), -- Rate limited API
    ('georegion-detector', 'loom-georegion', 50, 30000, 60000, 10000, 100),
    ('business-matcher', 'loom-business-matcher', 20, 60000, 120000, 20000, 500)
ON CONFLICT (service_name) DO NOTHING;

-- Advanced processing services
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms, max_partition_fetch_bytes
) VALUES
    ('slam-processor', 'loom-slam-processor', 1, 600000, 1200000, 120000, 104857600), -- 100MB for video
    ('gaze-detector', 'loom-gaze-detector', 5, 120000, 240000, 40000, 20971520),
    ('pose-detector', 'loom-pose-detector', 5, 120000, 240000, 40000, 20971520),
    ('object-hasher', 'loom-object-hasher', 20, 60000, 120000, 20000, 10485760),
    ('face-emotion-detector', 'loom-face-emotion', 5, 120000, 240000, 40000, 20971520)
ON CONFLICT (service_name) DO NOTHING;

-- Utility services
INSERT INTO pipeline_consumer_configs (
    service_name, consumer_group_id, max_poll_records, session_timeout_ms,
    max_poll_interval_ms, heartbeat_interval_ms
) VALUES
    ('notes-processor', 'loom-notes-processor', 50, 30000, 60000, 10000),
    ('email-parser', 'loom-email-parser', 50, 30000, 60000, 10000),
    ('calendar-enricher', 'loom-calendar-enricher', 50, 30000, 60000, 10000),
    ('embedding-generator', 'loom-embedding-gen', 20, 120000, 240000, 40000),
    ('power-analyzer', 'loom-power-analyzer', 100, 30000, 60000, 10000)
ON CONFLICT (service_name) DO NOTHING;

-- Create view for monitoring consumer configuration effectiveness
CREATE OR REPLACE VIEW v_consumer_config_monitoring AS
SELECT
    pcc.service_name,
    pcc.consumer_group_id,
    pcc.max_poll_records,
    pcc.max_poll_interval_ms,
    ps.replicas,
    ps.processing_timeout_seconds,
    ps.flow_name,
    pf.priority as flow_priority,
    pf.expected_events_per_second,
    COUNT(DISTINCT pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as input_topics_count,
    STRING_AGG(DISTINCT pst.topic_name, ', ' ORDER BY pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as input_topics,
    -- Calculate if timeout settings are appropriate
    CASE
        WHEN ps.processing_timeout_seconds IS NOT NULL
            AND (ps.processing_timeout_seconds * 1000) > pcc.max_poll_interval_ms
        THEN 'WARNING: Processing timeout exceeds poll interval'
        ELSE 'OK'
    END as timeout_check,
    -- Estimate max throughput
    (pcc.max_poll_records::NUMERIC / (pcc.max_poll_interval_ms::NUMERIC / 1000)) * ps.replicas as estimated_max_events_per_sec
FROM pipeline_consumer_configs pcc
JOIN pipeline_stages ps ON pcc.service_name = ps.service_name
JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
GROUP BY
    pcc.service_name, pcc.consumer_group_id, pcc.max_poll_records,
    pcc.max_poll_interval_ms, ps.replicas, ps.processing_timeout_seconds,
    ps.flow_name, pf.priority, pf.expected_events_per_second
ORDER BY
    CASE pf.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    pf.expected_events_per_second DESC;

-- Add comments for documentation
COMMENT ON TABLE pipeline_consumer_configs IS 'Stores Kafka consumer configuration for each processing service to optimize throughput and reliability';
COMMENT ON COLUMN pipeline_consumer_configs.max_poll_records IS 'Maximum number of records returned in a single poll() call';
COMMENT ON COLUMN pipeline_consumer_configs.session_timeout_ms IS 'Timeout used to detect consumer failures - consumer must send heartbeat within this time';
COMMENT ON COLUMN pipeline_consumer_configs.max_poll_interval_ms IS 'Maximum time between poll() calls before consumer is considered dead';
COMMENT ON COLUMN pipeline_consumer_configs.heartbeat_interval_ms IS 'Expected time between heartbeats to the consumer coordinator';
COMMENT ON COLUMN pipeline_consumer_configs.partition_assignment_strategy IS 'Strategy for assigning partitions to consumers: range, roundrobin, sticky, or cooperative-sticky';
COMMENT ON VIEW v_consumer_config_monitoring IS 'Monitoring view to validate consumer configurations against pipeline requirements';
