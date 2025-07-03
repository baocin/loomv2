-- Migration: Enhance pipeline views with API endpoint information
-- Purpose: Add API endpoint details to pipeline overview for complete data flow visibility

-- Create an enhanced pipeline overview that includes API endpoints
CREATE OR REPLACE VIEW v_pipeline_overview_with_api AS
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
    -- Input topics as simple array
    array_agg(DISTINCT pst_in.topic_name) FILTER (WHERE pst_in.topic_role = 'input') as input_topics,
    -- Input API endpoints
    array_agg(DISTINCT tae_in.api_endpoint) FILTER (WHERE pst_in.topic_role = 'input' AND tae_in.api_endpoint IS NOT NULL) as input_api_endpoints,
    -- Output topics
    array_agg(DISTINCT pst_out.topic_name) FILTER (WHERE pst_out.topic_role = 'output') as output_topics,
    -- Error topics
    array_agg(DISTINCT pst_err.topic_name) FILTER (WHERE pst_err.topic_role = 'error') as error_topics
FROM pipeline_flows pf
JOIN pipeline_stages ps ON pf.flow_name = ps.flow_name
LEFT JOIN pipeline_stage_topics pst_in ON ps.id = pst_in.stage_id AND pst_in.topic_role = 'input'
LEFT JOIN topic_api_endpoints tae_in ON pst_in.topic_name = tae_in.topic_name AND tae_in.is_primary = true
LEFT JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
LEFT JOIN pipeline_stage_topics pst_err ON ps.id = pst_err.stage_id AND pst_err.topic_role = 'error'
WHERE pf.is_active = true
GROUP BY pf.flow_name, pf.description, pf.priority, ps.stage_order, ps.stage_name,
         ps.service_name, ps.service_image, ps.replicas, ps.configuration, ps.id
ORDER BY pf.flow_name, ps.stage_order;

-- Create a view showing data flow from API to storage
CREATE OR REPLACE VIEW v_data_flow_api_to_storage AS
WITH api_topics AS (
    -- Topics that have API endpoints
    SELECT DISTINCT
        tae.topic_name,
        tae.api_endpoint,
        tae.api_method,
        kt.category,
        kt.source,
        kt.datatype
    FROM topic_api_endpoints tae
    JOIN kafka_topics kt ON tae.topic_name = kt.topic_name
    WHERE tae.is_primary = true
),
topic_to_table AS (
    -- Topics that have database tables
    SELECT DISTINCT
        ttc.topic_name,
        ttc.table_name,
        COUNT(tfm.id) as field_count
    FROM topic_table_configs ttc
    LEFT JOIN topic_field_mappings tfm ON ttc.topic_name = tfm.topic_name
    GROUP BY ttc.topic_name, ttc.table_name
),
pipeline_processing AS (
    -- Topics that go through pipeline processing
    SELECT DISTINCT
        pst_in.topic_name as input_topic,
        pf.flow_name,
        pst_out.topic_name as output_topic
    FROM pipeline_stage_topics pst_in
    JOIN pipeline_stages ps ON pst_in.stage_id = ps.id
    JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
    LEFT JOIN pipeline_stage_topics pst_out ON ps.id = pst_out.stage_id AND pst_out.topic_role = 'output'
    WHERE pst_in.topic_role = 'input'
)
SELECT
    at.api_endpoint,
    at.api_method,
    at.topic_name as ingestion_topic,
    pp.flow_name as processing_pipeline,
    pp.output_topic as processed_topic,
    COALESCE(ttt1.table_name, ttt2.table_name) as storage_table,
    CASE
        WHEN ttt1.table_name IS NOT NULL THEN 'Direct to DB'
        WHEN pp.flow_name IS NOT NULL THEN 'Via Pipeline'
        ELSE 'No Storage'
    END as storage_path
FROM api_topics at
LEFT JOIN topic_to_table ttt1 ON at.topic_name = ttt1.topic_name
LEFT JOIN pipeline_processing pp ON at.topic_name = pp.input_topic
LEFT JOIN topic_to_table ttt2 ON pp.output_topic = ttt2.topic_name
ORDER BY at.api_endpoint, at.topic_name;

-- Create a function to trace data flow for a specific API endpoint
CREATE OR REPLACE FUNCTION trace_api_data_flow(p_api_endpoint TEXT)
RETURNS TABLE(
    step INTEGER,
    component TEXT,
    component_type TEXT,
    details TEXT
) AS $$
BEGIN
    -- Step 1: API Endpoint
    RETURN QUERY
    SELECT
        1 as step,
        p_api_endpoint as component,
        'API Endpoint'::text as component_type,
        COALESCE(tae.api_description, 'No description') as details
    FROM topic_api_endpoints tae
    WHERE tae.api_endpoint = p_api_endpoint
    LIMIT 1;

    -- Step 2: Kafka Topics
    RETURN QUERY
    SELECT
        2 as step,
        tae.topic_name as component,
        'Kafka Topic'::text as component_type,
        kt.description as details
    FROM topic_api_endpoints tae
    JOIN kafka_topics kt ON tae.topic_name = kt.topic_name
    WHERE tae.api_endpoint = p_api_endpoint;

    -- Step 3: Pipeline Processing
    RETURN QUERY
    SELECT DISTINCT
        3 as step,
        pf.flow_name || ' - ' || ps.stage_name as component,
        'Pipeline Stage'::text as component_type,
        ps.service_name as details
    FROM topic_api_endpoints tae
    JOIN pipeline_stage_topics pst ON tae.topic_name = pst.topic_name
    JOIN pipeline_stages ps ON pst.stage_id = ps.id
    JOIN pipeline_flows pf ON ps.flow_name = pf.flow_name
    WHERE tae.api_endpoint = p_api_endpoint
      AND pst.topic_role = 'input';

    -- Step 4: Database Storage
    RETURN QUERY
    SELECT DISTINCT
        4 as step,
        ttc.table_name as component,
        'TimescaleDB Table'::text as component_type,
        'Stores ' || COUNT(tfm.id)::text || ' fields' as details
    FROM topic_api_endpoints tae
    JOIN topic_table_configs ttc ON tae.topic_name = ttc.topic_name
    LEFT JOIN topic_field_mappings tfm ON ttc.topic_name = tfm.topic_name
    WHERE tae.api_endpoint = p_api_endpoint
    GROUP BY ttc.table_name;
END;
$$ LANGUAGE plpgsql;

-- Create a summary view of API coverage
CREATE OR REPLACE VIEW v_api_coverage_summary AS
SELECT
    kt.category,
    COUNT(DISTINCT kt.topic_name) as total_topics,
    COUNT(DISTINCT tae.topic_name) as topics_with_api,
    COUNT(DISTINCT ttc.topic_name) as topics_with_storage,
    COUNT(DISTINCT pst.topic_name) as topics_in_pipelines,
    ROUND(100.0 * COUNT(DISTINCT tae.topic_name) / COUNT(DISTINCT kt.topic_name), 1) as api_coverage_percent
FROM kafka_topics kt
LEFT JOIN topic_api_endpoints tae ON kt.topic_name = tae.topic_name AND tae.is_primary = true
LEFT JOIN topic_table_configs ttc ON kt.topic_name = ttc.topic_name
LEFT JOIN pipeline_stage_topics pst ON kt.topic_name = pst.topic_name AND pst.topic_role = 'input'
WHERE kt.is_active = true
GROUP BY kt.category
ORDER BY kt.category;

-- Create a view showing which stages consume from API-fed topics
CREATE OR REPLACE VIEW v_pipeline_stages_with_api_sources AS
SELECT
    ps.flow_name,
    ps.stage_name,
    ps.service_name,
    pst.topic_name as input_topic,
    tae.api_endpoint,
    tae.api_method,
    tae.api_description
FROM pipeline_stages ps
JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id AND pst.topic_role = 'input'
JOIN topic_api_endpoints tae ON pst.topic_name = tae.topic_name AND tae.is_primary = true
ORDER BY ps.flow_name, ps.stage_order;

-- Comments
COMMENT ON VIEW v_pipeline_overview_with_api IS 'Enhanced pipeline overview including API endpoint information for input topics';
COMMENT ON VIEW v_data_flow_api_to_storage IS 'Complete data flow from API endpoints through Kafka topics and pipelines to database storage';
COMMENT ON FUNCTION trace_api_data_flow IS 'Trace the complete data flow path starting from a specific API endpoint';
COMMENT ON VIEW v_api_coverage_summary IS 'Summary of API endpoint coverage by topic category';
COMMENT ON VIEW v_pipeline_stages_with_api_sources IS 'Pipeline stages showing their input API endpoints';
