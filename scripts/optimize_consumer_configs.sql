-- Optimize consumer configurations for better performance
-- Based on the consumer type and processing requirements

-- High-throughput consumers (can process many messages quickly)
UPDATE pipeline_consumer_configs
SET
    max_poll_records = 1000,
    fetch_max_wait_ms = 100,
    fetch_min_bytes = 10240,  -- 10KB minimum
    session_timeout_ms = 30000,
    max_poll_interval_ms = 300000
WHERE service_name IN (
    'accelerometer-aggregator',
    'timescale-writer',
    'kafka-to-db-saver',
    'gps-geocoding-consumer',  -- GPS data is small and fast
    'step-counter',
    'power-analyzer',
    'app-lifecycle-processor',
    'app-event-enricher',
    'power-enricher'
);

-- Medium-throughput consumers (moderate processing time)
UPDATE pipeline_consumer_configs
SET
    max_poll_records = 200,
    fetch_max_wait_ms = 500,
    session_timeout_ms = 45000,
    max_poll_interval_ms = 300000
WHERE service_name IN (
    'audio-classifier',
    'activity-classifier',
    'motion-detector',
    'georegion-detector',
    'notes-processor',
    'email-parser',
    'calendar-enricher'
);

-- Low-throughput, high-processing consumers (AI models, heavy processing)
UPDATE pipeline_consumer_configs
SET
    max_poll_records = 10,
    fetch_max_wait_ms = 1000,
    session_timeout_ms = 120000,  -- 2 minutes
    max_poll_interval_ms = 600000,  -- 10 minutes
    request_timeout_ms = 605000
WHERE service_name IN (
    'kyutai-stt',
    'ocr-processor',
    'tesseract-ocr',
    'text-embedder',
    'embedding-generator',
    'mistral-reasoning',
    'x-url-processor'
);

-- Real-time processors (need low latency)
UPDATE pipeline_consumer_configs
SET
    max_poll_records = 50,
    fetch_max_wait_ms = 100,
    fetch_min_bytes = 1,  -- Don't wait for data
    session_timeout_ms = 30000,
    heartbeat_interval_ms = 10000,  -- More frequent heartbeats
    max_poll_interval_ms = 300000
WHERE service_name IN (
    'silero-vad',
    'image-preprocessor',
    'text-postprocessor',
    'power-pattern-detector',
    'business-matcher'
);

-- Verify the updates
SELECT
    service_name,
    consumer_group_id,
    max_poll_records,
    session_timeout_ms,
    max_poll_interval_ms,
    fetch_max_wait_ms
FROM pipeline_consumer_configs
ORDER BY max_poll_records DESC;
