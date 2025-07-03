-- Migration: Create Kafka Topic and Flow Schema Management Tables
-- Purpose: Centralize all Kafka topic definitions, schemas, and pipeline flows in the database
-- replacing scattered documentation across YAML files and markdown

-- 1. Master registry of all Kafka topics
CREATE TABLE IF NOT EXISTS kafka_topics (
    topic_name TEXT PRIMARY KEY,
    category TEXT NOT NULL,  -- device, media, analysis, external, etc.
    source TEXT NOT NULL,     -- audio, sensor, image, etc.
    datatype TEXT NOT NULL,   -- raw, processed, enriched, etc.
    stage TEXT,               -- optional stage indicator (e.g., filtered, classified)
    description TEXT NOT NULL,
    retention_days INTEGER NOT NULL DEFAULT 7,
    partitions INTEGER NOT NULL DEFAULT 3,
    replication_factor INTEGER NOT NULL DEFAULT 1,
    compression_type TEXT DEFAULT 'lz4' CHECK (compression_type IN ('none', 'gzip', 'snappy', 'lz4', 'zstd', 'producer')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    CONSTRAINT valid_topic_name CHECK (topic_name ~ '^[a-z0-9._]+$')
);

-- Create index for category-based queries
CREATE INDEX idx_kafka_topics_category ON kafka_topics(category);
CREATE INDEX idx_kafka_topics_active ON kafka_topics(is_active) WHERE is_active = true;

-- 2. JSON schemas for each topic with versioning
CREATE TABLE IF NOT EXISTS kafka_topic_schemas (
    id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL REFERENCES kafka_topics(topic_name) ON DELETE CASCADE,
    version TEXT NOT NULL,  -- v1, v2, etc.
    schema_json JSONB NOT NULL,  -- Full JSON schema
    schema_path TEXT,  -- Original file path reference (e.g., shared/schemas/device/audio/raw/v1.json)
    is_current BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(topic_name, version)
);

-- Ensure only one current schema per topic
CREATE UNIQUE INDEX idx_one_current_schema_per_topic 
    ON kafka_topic_schemas(topic_name) 
    WHERE is_current = true;

-- 3. High-level pipeline flow definitions
CREATE TABLE IF NOT EXISTS pipeline_flows (
    flow_name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    expected_events_per_second NUMERIC,
    average_event_size_bytes INTEGER,
    peak_multiplier NUMERIC DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- 4. Individual processing stages within flows
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id SERIAL PRIMARY KEY,
    flow_name TEXT NOT NULL REFERENCES pipeline_flows(flow_name) ON DELETE CASCADE,
    stage_name TEXT NOT NULL,
    stage_order INTEGER NOT NULL,
    service_name TEXT NOT NULL,
    service_image TEXT NOT NULL,
    replicas INTEGER DEFAULT 1 CHECK (replicas > 0),
    configuration JSONB,  -- Stage-specific config (model names, thresholds, etc.)
    processing_timeout_seconds INTEGER CHECK (processing_timeout_seconds > 0),
    retry_max_attempts INTEGER DEFAULT 3 CHECK (retry_max_attempts >= 0),
    retry_backoff_seconds INTEGER DEFAULT 1 CHECK (retry_backoff_seconds >= 0),
    sla_seconds NUMERIC CHECK (sla_seconds > 0),
    error_rate_threshold NUMERIC CHECK (error_rate_threshold >= 0 AND error_rate_threshold <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(flow_name, stage_name)
);

-- Index for ordered stage retrieval
CREATE INDEX idx_pipeline_stages_order ON pipeline_stages(flow_name, stage_order);

-- 5. Topic relationships for each stage (inputs, outputs, error topics)
CREATE TABLE IF NOT EXISTS pipeline_stage_topics (
    id SERIAL PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES pipeline_stages(id) ON DELETE CASCADE,
    topic_name TEXT NOT NULL REFERENCES kafka_topics(topic_name),
    topic_role TEXT NOT NULL CHECK (topic_role IN ('input', 'output', 'error')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(stage_id, topic_name, topic_role)
);

-- Index for finding stages by topic
CREATE INDEX idx_stage_topics_by_topic ON pipeline_stage_topics(topic_name);

-- 6. Database field mappings for kafka-to-db consumer
CREATE TABLE IF NOT EXISTS topic_field_mappings (
    id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL REFERENCES kafka_topics(topic_name) ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    source_field_path TEXT NOT NULL,  -- e.g., "data.ssid" or "ssid"
    target_column TEXT NOT NULL,
    data_type TEXT CHECK (data_type IN ('string', 'integer', 'float', 'boolean', 'timestamp', 'array', 'float_array', 'json')),
    transformation TEXT CHECK (transformation IN ('base64_decode', 'timestamp_parse', 'json_stringify')),
    is_required BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(topic_name, source_field_path, target_column)
);

-- Index for efficient lookups by topic
CREATE INDEX idx_field_mappings_by_topic ON topic_field_mappings(topic_name);

-- 7. Configuration for kafka-to-db consumer
CREATE TABLE IF NOT EXISTS topic_table_configs (
    topic_name TEXT PRIMARY KEY REFERENCES kafka_topics(topic_name) ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    upsert_key TEXT NOT NULL DEFAULT 'device_id, timestamp',
    conflict_strategy TEXT DEFAULT 'ignore' CHECK (conflict_strategy IN ('ignore', 'update', 'replace')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Create update trigger for timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_kafka_topics_updated_at BEFORE UPDATE ON kafka_topics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pipeline_flows_updated_at BEFORE UPDATE ON pipeline_flows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_topic_table_configs_updated_at BEFORE UPDATE ON topic_table_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 9. Useful views for querying

-- Active topics with their current schemas
CREATE VIEW v_active_topics AS
SELECT 
    kt.topic_name,
    kt.category,
    kt.source,
    kt.datatype,
    kt.stage,
    kt.description,
    kt.retention_days,
    kts.version as schema_version,
    kts.schema_json,
    kt.created_at,
    kt.updated_at
FROM kafka_topics kt
LEFT JOIN kafka_topic_schemas kts ON kt.topic_name = kts.topic_name AND kts.is_current = true
WHERE kt.is_active = true
ORDER BY kt.category, kt.source, kt.datatype;

-- Complete pipeline overview with stages and topics
CREATE VIEW v_pipeline_overview AS
SELECT 
    pf.flow_name,
    pf.description as flow_description,
    pf.priority,
    ps.stage_order,
    ps.stage_name,
    ps.service_name,
    ps.service_image,
    ps.replicas,
    ps.configuration,
    array_agg(DISTINCT pst_in.topic_name) FILTER (WHERE pst_in.topic_role = 'input') as input_topics,
    array_agg(DISTINCT pst_out.topic_name) FILTER (WHERE pst_out.topic_role = 'output') as output_topics,
    array_agg(DISTINCT pst_err.topic_name) FILTER (WHERE pst_err.topic_role = 'error') as error_topics
FROM pipeline_flows pf
JOIN pipeline_stages ps ON pf.flow_name = ps.flow_name
LEFT JOIN pipeline_stage_topics pst_in ON ps.id = pst_in.stage_id AND pst_in.topic_role = 'input'
LEFT JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
LEFT JOIN pipeline_stage_topics pst_err ON ps.id = pst_err.stage_id AND pst_err.topic_role = 'error'
WHERE pf.is_active = true
GROUP BY pf.flow_name, pf.description, pf.priority, ps.stage_order, ps.stage_name, 
         ps.service_name, ps.service_image, ps.replicas, ps.configuration
ORDER BY pf.flow_name, ps.stage_order;

-- Topic dependencies - which topics are produced from which
CREATE VIEW v_topic_dependencies AS
WITH topic_flow AS (
    SELECT DISTINCT
        pst_in.topic_name as source_topic,
        pst_out.topic_name as target_topic,
        ps.service_name as processing_service,
        pf.flow_name
    FROM pipeline_stages ps
    JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
    JOIN pipeline_stage_topics pst_in ON ps.id = pst_in.stage_id AND pst_in.topic_role = 'input'
    JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
    WHERE pf.is_active = true
)
SELECT 
    source_topic,
    target_topic,
    processing_service,
    flow_name,
    kt_source.description as source_description,
    kt_target.description as target_description
FROM topic_flow
JOIN kafka_topics kt_source ON topic_flow.source_topic = kt_source.topic_name
JOIN kafka_topics kt_target ON topic_flow.target_topic = kt_target.topic_name
ORDER BY source_topic, target_topic;

-- 10. Utility functions

-- Get topic schema by name and version (defaults to current)
CREATE OR REPLACE FUNCTION get_topic_schema(
    p_topic_name TEXT,
    p_version TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
BEGIN
    IF p_version IS NULL THEN
        RETURN (
            SELECT schema_json 
            FROM kafka_topic_schemas 
            WHERE topic_name = p_topic_name AND is_current = true
        );
    ELSE
        RETURN (
            SELECT schema_json 
            FROM kafka_topic_schemas 
            WHERE topic_name = p_topic_name AND version = p_version
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Get complete pipeline configuration as JSON
CREATE OR REPLACE FUNCTION get_pipeline_config(p_flow_name TEXT)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'flow_name', pf.flow_name,
        'description', pf.description,
        'priority', pf.priority,
        'data_volume', jsonb_build_object(
            'expected_events_per_second', pf.expected_events_per_second,
            'average_event_size_bytes', pf.average_event_size_bytes,
            'peak_multiplier', pf.peak_multiplier
        ),
        'stages', (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'name', ps.stage_name,
                    'order', ps.stage_order,
                    'service', jsonb_build_object(
                        'name', ps.service_name,
                        'image', ps.service_image,
                        'replicas', ps.replicas
                    ),
                    'configuration', ps.configuration,
                    'processing', jsonb_build_object(
                        'timeout_seconds', ps.processing_timeout_seconds,
                        'retry_max_attempts', ps.retry_max_attempts,
                        'retry_backoff_seconds', ps.retry_backoff_seconds
                    ),
                    'monitoring', jsonb_build_object(
                        'sla_seconds', ps.sla_seconds,
                        'error_rate_threshold', ps.error_rate_threshold
                    ),
                    'input_topics', (
                        SELECT array_agg(pst.topic_name)
                        FROM pipeline_stage_topics pst
                        WHERE pst.stage_id = ps.id AND pst.topic_role = 'input'
                    ),
                    'output_topics', (
                        SELECT array_agg(pst.topic_name)
                        FROM pipeline_stage_topics pst
                        WHERE pst.stage_id = ps.id AND pst.topic_role = 'output'
                    ),
                    'error_topics', (
                        SELECT array_agg(pst.topic_name)
                        FROM pipeline_stage_topics pst
                        WHERE pst.stage_id = ps.id AND pst.topic_role = 'error'
                    )
                ) ORDER BY ps.stage_order
            )
            FROM pipeline_stages ps
            WHERE ps.flow_name = pf.flow_name
        )
    ) INTO result
    FROM pipeline_flows pf
    WHERE pf.flow_name = p_flow_name AND pf.is_active = true;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Validate topic name follows naming convention
CREATE OR REPLACE FUNCTION validate_topic_name(p_topic_name TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check basic pattern
    IF p_topic_name !~ '^[a-z0-9._]+$' THEN
        RETURN FALSE;
    END IF;
    
    -- Check structure: category.source.datatype[.stage]
    IF p_topic_name !~ '^[a-z0-9]+\.[a-z0-9]+\.[a-z0-9]+(\.[a-z0-9]+)?$' THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Add constraint to validate topic names
ALTER TABLE kafka_topics ADD CONSTRAINT valid_topic_structure 
    CHECK (validate_topic_name(topic_name));

-- Comments for documentation
COMMENT ON TABLE kafka_topics IS 'Master registry of all Kafka topics in the Loom v2 system';
COMMENT ON TABLE kafka_topic_schemas IS 'JSON schemas for Kafka topics with version history';
COMMENT ON TABLE pipeline_flows IS 'High-level data processing pipeline definitions';
COMMENT ON TABLE pipeline_stages IS 'Individual processing stages within pipeline flows';
COMMENT ON TABLE pipeline_stage_topics IS 'Topic relationships (input/output/error) for pipeline stages';
COMMENT ON TABLE topic_field_mappings IS 'Field mappings for kafka-to-db consumer';
COMMENT ON TABLE topic_table_configs IS 'Configuration for kafka-to-db consumer per topic';
COMMENT ON VIEW v_active_topics IS 'All active Kafka topics with their current schemas';
COMMENT ON VIEW v_pipeline_overview IS 'Complete view of all pipeline flows with stages and topic relationships';
COMMENT ON VIEW v_topic_dependencies IS 'Data lineage view showing which topics produce which other topics';