-- Migration: Add consumer metrics tables for monitoring and optimization
-- This migration creates tables to track consumer lag and processing performance

-- Create consumer lag history table
CREATE TABLE IF NOT EXISTS consumer_lag_history (
    id BIGSERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    topic TEXT NOT NULL,
    partition INTEGER NOT NULL,
    lag BIGINT NOT NULL,
    consumer_offset BIGINT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT fk_lag_history_service
        FOREIGN KEY (service_name)
        REFERENCES pipeline_stages(service_name)
        ON DELETE CASCADE
);

-- Create hypertable for time-series data
SELECT create_hypertable('consumer_lag_history', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create index for lag queries
CREATE INDEX IF NOT EXISTS idx_consumer_lag_history_service_time
    ON consumer_lag_history (service_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_consumer_lag_history_topic_partition
    ON consumer_lag_history (topic, partition, timestamp DESC);

-- Create consumer processing metrics table
CREATE TABLE IF NOT EXISTS consumer_processing_metrics (
    id BIGSERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    messages_processed INTEGER NOT NULL,
    processing_time_ms NUMERIC NOT NULL,
    messages_per_second NUMERIC NOT NULL,
    memory_usage_mb NUMERIC,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT fk_processing_metrics_service
        FOREIGN KEY (service_name)
        REFERENCES pipeline_stages(service_name)
        ON DELETE CASCADE
);

-- Create hypertable for processing metrics
SELECT create_hypertable('consumer_processing_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create index for processing metrics queries
CREATE INDEX IF NOT EXISTS idx_consumer_processing_metrics_service_time
    ON consumer_processing_metrics (service_name, timestamp DESC);

-- Add retention policies (keep 7 days of detailed metrics)
SELECT add_retention_policy('consumer_lag_history', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('consumer_processing_metrics', INTERVAL '7 days', if_not_exists => TRUE);

-- Create continuous aggregates for hourly statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS consumer_lag_hourly
WITH (timescaledb.continuous) AS
SELECT
    service_name,
    topic,
    partition,
    time_bucket('1 hour', timestamp) AS hour,
    AVG(lag) as avg_lag,
    MAX(lag) as max_lag,
    MIN(lag) as min_lag,
    COUNT(*) as sample_count
FROM consumer_lag_history
GROUP BY service_name, topic, partition, hour
WITH NO DATA;

-- Create continuous aggregate for processing metrics
CREATE MATERIALIZED VIEW IF NOT EXISTS consumer_processing_hourly
WITH (timescaledb.continuous) AS
SELECT
    service_name,
    time_bucket('1 hour', timestamp) AS hour,
    SUM(messages_processed) as total_messages,
    AVG(processing_time_ms) as avg_processing_time_ms,
    AVG(messages_per_second) as avg_messages_per_second,
    AVG(memory_usage_mb) as avg_memory_mb,
    MAX(memory_usage_mb) as max_memory_mb,
    COUNT(*) as sample_count
FROM consumer_processing_metrics
GROUP BY service_name, hour
WITH NO DATA;

-- Add retention to continuous aggregates (keep 30 days)
SELECT add_retention_policy('consumer_lag_hourly', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('consumer_processing_hourly', INTERVAL '30 days', if_not_exists => TRUE);

-- Create refresh policies for continuous aggregates
SELECT add_continuous_aggregate_policy('consumer_lag_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('consumer_processing_hourly',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Create view for current consumer lag
CREATE OR REPLACE VIEW v_current_consumer_lag AS
WITH latest_lag AS (
    SELECT DISTINCT ON (service_name, topic, partition)
        service_name,
        topic,
        partition,
        lag,
        consumer_offset,
        timestamp
    FROM consumer_lag_history
    WHERE timestamp > NOW() - INTERVAL '5 minutes'
    ORDER BY service_name, topic, partition, timestamp DESC
)
SELECT
    l.service_name,
    l.topic,
    COUNT(DISTINCT l.partition) as partition_count,
    SUM(l.lag) as total_lag,
    AVG(l.lag) as avg_lag_per_partition,
    MAX(l.lag) as max_partition_lag,
    MAX(l.timestamp) as last_update
FROM latest_lag l
GROUP BY l.service_name, l.topic
ORDER BY SUM(l.lag) DESC;

-- Create alert view for high lag
CREATE OR REPLACE VIEW v_consumer_lag_alerts AS
SELECT
    clh.service_name,
    clh.topic,
    AVG(clh.lag) as avg_lag,
    MAX(clh.lag) as max_lag,
    pcc.max_poll_records,
    pcc.max_poll_interval_ms,
    CASE
        WHEN AVG(clh.lag) > 10000 THEN 'critical'
        WHEN AVG(clh.lag) > 1000 THEN 'warning'
        ELSE 'ok'
    END as alert_level,
    CASE
        WHEN AVG(clh.lag) > 10000 THEN 'Consumer severely lagging - may need scaling or optimization'
        WHEN AVG(clh.lag) > 1000 THEN 'Consumer lag increasing - monitor closely'
        ELSE 'Consumer lag within acceptable range'
    END as alert_message
FROM consumer_lag_history clh
JOIN pipeline_consumer_configs pcc ON clh.service_name = pcc.service_name
WHERE clh.timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY clh.service_name, clh.topic, pcc.max_poll_records, pcc.max_poll_interval_ms
HAVING AVG(clh.lag) > 100
ORDER BY AVG(clh.lag) DESC;

-- Add comments
COMMENT ON TABLE consumer_lag_history IS 'Time-series data tracking Kafka consumer lag per partition';
COMMENT ON TABLE consumer_processing_metrics IS 'Time-series data tracking consumer processing performance';
COMMENT ON VIEW v_current_consumer_lag IS 'Current consumer lag aggregated by service and topic';
COMMENT ON VIEW v_consumer_lag_alerts IS 'Consumer lag alerts for monitoring and scaling decisions';
