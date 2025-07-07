-- Migration: Add consumer activity logging table
-- This migration creates a table to track Kafka consumer activity, including
-- the last consumed and produced messages for each consumer service

-- Create extension for UUID generation if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the consumer activity logging table
CREATE TABLE IF NOT EXISTS logged_consumer_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    consumer_id TEXT NOT NULL UNIQUE, -- Service name of the consumer
    last_consumed_message JSONB, -- The last message consumed from input topic
    last_produced_message JSONB, -- The last message produced to output topic
    message_consumed_at TIMESTAMPTZ, -- When the message was consumed
    message_produced_at TIMESTAMPTZ, -- When the output was produced
    last_complete_processed_consumed_message JSONB, -- Previous complete consumed message
    last_complete_processed_produced_message JSONB, -- Previous complete produced message
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Indexes for performance
    CONSTRAINT valid_consumer_id CHECK (consumer_id != ''),
    CONSTRAINT consumed_before_produced CHECK (
        message_produced_at IS NULL OR
        message_consumed_at IS NULL OR
        message_consumed_at <= message_produced_at
    )
);

-- Create indexes for common queries
CREATE INDEX idx_consumer_activity_consumer_id ON logged_consumer_activity(consumer_id);
CREATE INDEX idx_consumer_activity_consumed_at ON logged_consumer_activity(message_consumed_at);
CREATE INDEX idx_consumer_activity_produced_at ON logged_consumer_activity(message_produced_at);
CREATE INDEX idx_consumer_activity_updated_at ON logged_consumer_activity(updated_at);

-- Create trigger to update the updated_at timestamp
CREATE TRIGGER update_logged_consumer_activity_updated_at
    BEFORE UPDATE ON logged_consumer_activity
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add foreign key constraint to ensure consumer exists in pipeline
ALTER TABLE logged_consumer_activity
    ADD CONSTRAINT fk_consumer_activity_service
    FOREIGN KEY (consumer_id)
    REFERENCES pipeline_stages(service_name)
    ON DELETE CASCADE;

-- Create a view to monitor consumer processing lag and activity
CREATE OR REPLACE VIEW v_consumer_activity_monitoring AS
WITH latest_activity AS (
    SELECT
        lca.consumer_id,
        lca.message_consumed_at,
        lca.message_produced_at,
        lca.last_consumed_message,
        lca.last_produced_message,
        -- Calculate processing time in milliseconds
        CASE
            WHEN lca.message_produced_at IS NOT NULL AND lca.message_consumed_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (lca.message_produced_at - lca.message_consumed_at)) * 1000
            ELSE NULL
        END as processing_time_ms,
        -- Calculate time since last consumption
        EXTRACT(EPOCH FROM (NOW() - lca.message_consumed_at)) as seconds_since_consumed,
        -- Calculate time since last production
        CASE
            WHEN lca.message_produced_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (NOW() - lca.message_produced_at))
            ELSE NULL
        END as seconds_since_produced
    FROM logged_consumer_activity lca
)
SELECT
    la.consumer_id,
    ps.flow_name,
    pf.priority as flow_priority,
    la.message_consumed_at,
    la.message_produced_at,
    la.processing_time_ms,
    la.seconds_since_consumed,
    la.seconds_since_produced,
    -- Extract message metadata if available
    la.last_consumed_message->>'device_id' as last_device_id,
    la.last_consumed_message->>'topic' as consumed_from_topic,
    jsonb_typeof(la.last_consumed_message) as consumed_message_type,
    jsonb_typeof(la.last_produced_message) as produced_message_type,
    -- Processing status
    CASE
        WHEN la.message_consumed_at IS NULL THEN 'never_consumed'
        WHEN la.message_produced_at IS NULL AND la.seconds_since_consumed < 60 THEN 'processing'
        WHEN la.message_produced_at IS NULL AND la.seconds_since_consumed >= 60 THEN 'stalled'
        WHEN la.processing_time_ms < 1000 THEN 'fast'
        WHEN la.processing_time_ms < 10000 THEN 'normal'
        ELSE 'slow'
    END as processing_status,
    -- Alert flags
    CASE
        WHEN la.seconds_since_consumed > 300 THEN true -- No activity for 5 minutes
        ELSE false
    END as is_inactive,
    CASE
        WHEN la.message_consumed_at IS NOT NULL
            AND la.message_produced_at IS NULL
            AND la.seconds_since_consumed > 120 THEN true -- Consumed but not produced for 2 minutes
        ELSE false
    END as is_stuck
FROM latest_activity la
JOIN pipeline_stages ps ON la.consumer_id = ps.service_name
JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
ORDER BY
    CASE pf.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    la.seconds_since_consumed DESC NULLS LAST;

-- Create a function to upsert consumer activity
CREATE OR REPLACE FUNCTION upsert_consumer_activity(
    p_consumer_id TEXT,
    p_consumed_message JSONB DEFAULT NULL,
    p_produced_message JSONB DEFAULT NULL,
    p_consumed_at TIMESTAMPTZ DEFAULT NULL,
    p_produced_at TIMESTAMPTZ DEFAULT NULL
) RETURNS logged_consumer_activity AS $$
DECLARE
    v_result logged_consumer_activity;
BEGIN
    -- Insert or update the consumer activity
    INSERT INTO logged_consumer_activity (
        consumer_id,
        last_consumed_message,
        last_produced_message,
        message_consumed_at,
        message_produced_at
    ) VALUES (
        p_consumer_id,
        p_consumed_message,
        p_produced_message,
        p_consumed_at,
        p_produced_at
    )
    ON CONFLICT (consumer_id) DO UPDATE SET
        -- Update consumed message info if provided
        last_consumed_message = CASE
            WHEN p_consumed_message IS NOT NULL THEN p_consumed_message
            ELSE logged_consumer_activity.last_consumed_message
        END,
        message_consumed_at = CASE
            WHEN p_consumed_at IS NOT NULL THEN p_consumed_at
            ELSE logged_consumer_activity.message_consumed_at
        END,
        -- Update produced message info if provided
        last_produced_message = CASE
            WHEN p_produced_message IS NOT NULL THEN p_produced_message
            WHEN p_consumed_message IS NOT NULL THEN NULL -- Clear produced when new message consumed
            ELSE logged_consumer_activity.last_produced_message
        END,
        message_produced_at = CASE
            WHEN p_produced_at IS NOT NULL THEN p_produced_at
            WHEN p_consumed_message IS NOT NULL THEN NULL -- Clear produced time when new message consumed
            ELSE logged_consumer_activity.message_produced_at
        END,
        -- Move current to "last complete" when both consumed and produced are being updated
        last_complete_processed_consumed_message = CASE
            WHEN p_produced_message IS NOT NULL
                AND logged_consumer_activity.last_consumed_message IS NOT NULL
            THEN logged_consumer_activity.last_consumed_message
            ELSE logged_consumer_activity.last_complete_processed_consumed_message
        END,
        last_complete_processed_produced_message = CASE
            WHEN p_produced_message IS NOT NULL
                AND logged_consumer_activity.last_consumed_message IS NOT NULL
            THEN p_produced_message
            ELSE logged_consumer_activity.last_complete_processed_produced_message
        END,
        updated_at = NOW()
    RETURNING * INTO v_result;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE logged_consumer_activity IS 'Tracks the last consumed and produced messages for each Kafka consumer service';
COMMENT ON COLUMN logged_consumer_activity.consumer_id IS 'Service name from pipeline_stages that uniquely identifies the consumer';
COMMENT ON COLUMN logged_consumer_activity.last_consumed_message IS 'The most recent message consumed from the input topic';
COMMENT ON COLUMN logged_consumer_activity.last_produced_message IS 'The most recent message produced to the output topic';
COMMENT ON COLUMN logged_consumer_activity.message_consumed_at IS 'Timestamp when the last message was consumed';
COMMENT ON COLUMN logged_consumer_activity.message_produced_at IS 'Timestamp when the last output was produced';
COMMENT ON COLUMN logged_consumer_activity.last_complete_processed_consumed_message IS 'Previous fully processed consumed message (both consumed and produced)';
COMMENT ON COLUMN logged_consumer_activity.last_complete_processed_produced_message IS 'Previous fully processed produced message';
COMMENT ON FUNCTION upsert_consumer_activity IS 'Upserts consumer activity data, handling both consumption and production events';
COMMENT ON VIEW v_consumer_activity_monitoring IS 'Real-time monitoring view for consumer processing status and health';

-- Grant permissions to the loom user
GRANT ALL ON TABLE logged_consumer_activity TO loom;
GRANT ALL ON FUNCTION upsert_consumer_activity TO loom;
