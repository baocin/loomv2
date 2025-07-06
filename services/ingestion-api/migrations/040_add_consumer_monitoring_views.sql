-- Migration: Add monitoring views for consumer performance tracking
-- This migration creates views to monitor the effectiveness of consumer configurations

-- Create a table to track consumer lag over time
CREATE TABLE IF NOT EXISTS consumer_lag_history (
    id SERIAL PRIMARY KEY,
    consumer_group_id TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    partition_id INTEGER NOT NULL,
    current_offset BIGINT NOT NULL,
    log_end_offset BIGINT NOT NULL,
    lag BIGINT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_offsets CHECK (current_offset >= 0 AND log_end_offset >= current_offset)
);

-- Create index for efficient querying
CREATE INDEX idx_consumer_lag_history_lookup
    ON consumer_lag_history(consumer_group_id, topic_name, timestamp DESC);

-- Convert to TimescaleDB hypertable for efficient time-series storage
SELECT create_hypertable('consumer_lag_history', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create retention policy (keep 7 days of lag history)
SELECT add_retention_policy('consumer_lag_history', INTERVAL '7 days', if_not_exists => TRUE);

-- Create a table to track processing performance
CREATE TABLE IF NOT EXISTS consumer_processing_metrics (
    id SERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    consumer_group_id TEXT NOT NULL,
    batch_size INTEGER NOT NULL,
    processing_duration_ms INTEGER NOT NULL,
    messages_processed INTEGER NOT NULL,
    messages_failed INTEGER DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT valid_metrics CHECK (
        batch_size > 0 AND
        processing_duration_ms >= 0 AND
        messages_processed >= 0 AND
        messages_failed >= 0
    )
);

-- Create index for efficient querying
CREATE INDEX idx_consumer_processing_metrics_lookup
    ON consumer_processing_metrics(service_name, timestamp DESC);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('consumer_processing_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

-- Create retention policy (keep 30 days of processing metrics)
SELECT add_retention_policy('consumer_processing_metrics', INTERVAL '30 days', if_not_exists => TRUE);

-- Create monitoring view for consumer performance
CREATE OR REPLACE VIEW v_consumer_performance_monitor AS
WITH consumer_stats AS (
    SELECT
        pcc.service_name,
        pcc.consumer_group_id,
        pcc.max_poll_records,
        pcc.max_poll_interval_ms,
        ps.flow_name,
        pf.priority as flow_priority,
        pf.expected_events_per_second,
        -- Get latest lag data
        COALESCE(
            (SELECT SUM(lag)
             FROM consumer_lag_history clh
             WHERE clh.consumer_group_id = pcc.consumer_group_id
               AND clh.timestamp > NOW() - INTERVAL '5 minutes'
             GROUP BY clh.consumer_group_id
             ORDER BY MAX(clh.timestamp) DESC
             LIMIT 1
            ), 0
        ) as current_total_lag,
        -- Get average processing time
        COALESCE(
            (SELECT AVG(processing_duration_ms)
             FROM consumer_processing_metrics cpm
             WHERE cpm.service_name = pcc.service_name
               AND cpm.timestamp > NOW() - INTERVAL '1 hour'
            ), 0
        ) as avg_processing_time_ms,
        -- Get average batch size
        COALESCE(
            (SELECT AVG(batch_size)
             FROM consumer_processing_metrics cpm
             WHERE cpm.service_name = pcc.service_name
               AND cpm.timestamp > NOW() - INTERVAL '1 hour'
            ), 0
        ) as avg_batch_size,
        -- Get error rate
        COALESCE(
            (SELECT
                CASE
                    WHEN SUM(messages_processed + messages_failed) > 0
                    THEN SUM(messages_failed)::NUMERIC / SUM(messages_processed + messages_failed)
                    ELSE 0
                END
             FROM consumer_processing_metrics cpm
             WHERE cpm.service_name = pcc.service_name
               AND cpm.timestamp > NOW() - INTERVAL '1 hour'
            ), 0
        ) as error_rate
    FROM pipeline_consumer_configs pcc
    JOIN pipeline_stages ps ON pcc.service_name = ps.service_name
    JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
),
performance_analysis AS (
    SELECT
        *,
        -- Calculate if consumer is keeping up
        CASE
            WHEN current_total_lag > 10000 THEN 'CRITICAL'
            WHEN current_total_lag > 1000 THEN 'WARNING'
            WHEN current_total_lag > 100 THEN 'WATCH'
            ELSE 'HEALTHY'
        END as lag_status,
        -- Check if processing time is within limits
        CASE
            WHEN avg_processing_time_ms > max_poll_interval_ms * 0.8 THEN 'TOO_SLOW'
            WHEN avg_processing_time_ms > max_poll_interval_ms * 0.5 THEN 'MARGINAL'
            ELSE 'GOOD'
        END as processing_speed,
        -- Calculate efficiency
        CASE
            WHEN avg_batch_size > 0 AND max_poll_records > 0
            THEN ROUND((avg_batch_size::NUMERIC / max_poll_records) * 100, 2)
            ELSE 0
        END as batch_efficiency_percent,
        -- Recommend configuration changes
        CASE
            WHEN current_total_lag > 10000 AND avg_batch_size < max_poll_records * 0.5
                THEN 'Increase max_poll_records - consumer has capacity'
            WHEN avg_processing_time_ms > max_poll_interval_ms * 0.8
                THEN 'Decrease max_poll_records or increase timeouts'
            WHEN error_rate > 0.1
                THEN 'High error rate - check processing logic'
            WHEN current_total_lag < 10 AND avg_batch_size < 10
                THEN 'Very low volume - consider reducing resources'
            ELSE 'Configuration appears optimal'
        END as recommendation
    FROM consumer_stats
)
SELECT
    service_name,
    consumer_group_id,
    flow_name,
    flow_priority,
    expected_events_per_second,
    current_total_lag,
    lag_status,
    avg_processing_time_ms,
    max_poll_interval_ms,
    processing_speed,
    avg_batch_size,
    max_poll_records,
    batch_efficiency_percent,
    error_rate,
    recommendation
FROM performance_analysis
ORDER BY
    CASE lag_status
        WHEN 'CRITICAL' THEN 1
        WHEN 'WARNING' THEN 2
        WHEN 'WATCH' THEN 3
        ELSE 4
    END,
    current_total_lag DESC;

-- Create alert view for consumers that need attention
CREATE OR REPLACE VIEW v_consumer_alerts AS
SELECT
    service_name,
    consumer_group_id,
    flow_priority,
    lag_status,
    current_total_lag,
    processing_speed,
    error_rate,
    recommendation,
    CASE
        WHEN lag_status = 'CRITICAL' OR processing_speed = 'TOO_SLOW' OR error_rate > 0.2
        THEN 'IMMEDIATE_ACTION'
        WHEN lag_status = 'WARNING' OR processing_speed = 'MARGINAL' OR error_rate > 0.1
        THEN 'INVESTIGATE'
        ELSE 'MONITOR'
    END as action_required
FROM v_consumer_performance_monitor
WHERE lag_status IN ('CRITICAL', 'WARNING', 'WATCH')
   OR processing_speed IN ('TOO_SLOW', 'MARGINAL')
   OR error_rate > 0.05
ORDER BY
    CASE flow_priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    current_total_lag DESC;

-- Create historical performance tracking view
CREATE OR REPLACE VIEW v_consumer_performance_history AS
WITH hourly_stats AS (
    SELECT
        service_name,
        time_bucket('1 hour', timestamp) as hour,
        AVG(processing_duration_ms) as avg_processing_ms,
        AVG(batch_size) as avg_batch_size,
        SUM(messages_processed) as total_messages,
        SUM(messages_failed) as total_failures,
        COUNT(*) as batch_count
    FROM consumer_processing_metrics
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY service_name, hour
),
hourly_lag AS (
    SELECT
        consumer_group_id,
        time_bucket('1 hour', timestamp) as hour,
        MAX(lag) as max_lag,
        AVG(lag) as avg_lag
    FROM consumer_lag_history
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY consumer_group_id, hour
)
SELECT
    hs.service_name,
    pcc.consumer_group_id,
    hs.hour,
    hs.avg_processing_ms,
    hs.avg_batch_size,
    hs.total_messages,
    hs.total_failures,
    hs.batch_count,
    ROUND(hs.total_messages::NUMERIC / EXTRACT(EPOCH FROM INTERVAL '1 hour'), 2) as messages_per_second,
    hl.max_lag,
    hl.avg_lag,
    CASE
        WHEN hs.total_messages + hs.total_failures > 0
        THEN ROUND(hs.total_failures::NUMERIC / (hs.total_messages + hs.total_failures) * 100, 2)
        ELSE 0
    END as error_rate_percent
FROM hourly_stats hs
JOIN pipeline_consumer_configs pcc ON hs.service_name = pcc.service_name
LEFT JOIN hourly_lag hl ON pcc.consumer_group_id = hl.consumer_group_id AND hs.hour = hl.hour
ORDER BY hs.service_name, hs.hour DESC;

-- Create function to record consumer lag
CREATE OR REPLACE FUNCTION record_consumer_lag(
    p_consumer_group_id TEXT,
    p_topic_name TEXT,
    p_partition_id INTEGER,
    p_current_offset BIGINT,
    p_log_end_offset BIGINT
) RETURNS VOID AS $$
BEGIN
    INSERT INTO consumer_lag_history (
        consumer_group_id,
        topic_name,
        partition_id,
        current_offset,
        log_end_offset,
        lag
    ) VALUES (
        p_consumer_group_id,
        p_topic_name,
        p_partition_id,
        p_current_offset,
        p_log_end_offset,
        p_log_end_offset - p_current_offset
    );
END;
$$ LANGUAGE plpgsql;

-- Create function to record processing metrics
CREATE OR REPLACE FUNCTION record_processing_metrics(
    p_service_name TEXT,
    p_consumer_group_id TEXT,
    p_batch_size INTEGER,
    p_processing_duration_ms INTEGER,
    p_messages_processed INTEGER,
    p_messages_failed INTEGER DEFAULT 0
) RETURNS VOID AS $$
BEGIN
    INSERT INTO consumer_processing_metrics (
        service_name,
        consumer_group_id,
        batch_size,
        processing_duration_ms,
        messages_processed,
        messages_failed
    ) VALUES (
        p_service_name,
        p_consumer_group_id,
        p_batch_size,
        p_processing_duration_ms,
        p_messages_processed,
        p_messages_failed
    );
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON VIEW v_consumer_performance_monitor IS 'Real-time monitoring of consumer performance and configuration effectiveness';
COMMENT ON VIEW v_consumer_alerts IS 'Active alerts for consumers requiring attention';
COMMENT ON VIEW v_consumer_performance_history IS 'Historical performance metrics for trend analysis';
COMMENT ON FUNCTION record_consumer_lag IS 'Record consumer lag metrics for monitoring';
COMMENT ON FUNCTION record_processing_metrics IS 'Record processing performance metrics';
