-- Migration: Add API endpoint mapping to topics
-- Purpose: Track which FastAPI endpoints produce data for each Kafka topic

-- Create a separate table for API endpoint mappings (many-to-many relationship)
CREATE TABLE IF NOT EXISTS topic_api_endpoints (
    id SERIAL PRIMARY KEY,
    topic_name TEXT NOT NULL REFERENCES kafka_topics(topic_name) ON DELETE CASCADE,
    api_endpoint TEXT NOT NULL,
    api_method TEXT NOT NULL DEFAULT 'POST',
    api_description TEXT,
    is_primary BOOLEAN DEFAULT false,  -- Mark the primary endpoint for a topic
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(topic_name, api_endpoint, api_method)
);

-- Create indexes for lookups
CREATE INDEX IF NOT EXISTS idx_topic_api_endpoints_topic ON topic_api_endpoints(topic_name);
CREATE INDEX IF NOT EXISTS idx_topic_api_endpoints_endpoint ON topic_api_endpoints(api_endpoint);
CREATE INDEX IF NOT EXISTS idx_topic_api_endpoints_primary ON topic_api_endpoints(topic_name) WHERE is_primary = true;

-- Insert API endpoint mappings based on ingestion-api routes
-- Audio endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.audio.raw', '/audio/upload', 'POST', 'Upload audio chunks in base64 format', true),
('device.audio.raw', '/audio/stream/{device_id}', 'WebSocket', 'Real-time audio streaming via WebSocket', false);

-- Sensor endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.sensor.gps.raw', '/sensor/gps', 'POST', 'GPS coordinates with accuracy metadata', true),
('device.sensor.gps.raw', '/sensor/batch', 'POST', 'Batch upload multiple sensor readings', false),
('device.sensor.accelerometer.raw', '/sensor/accelerometer', 'POST', '3-axis accelerometer motion data', true),
('device.sensor.accelerometer.raw', '/sensor/batch', 'POST', 'Batch upload multiple sensor readings', false),
('device.sensor.barometer.raw', '/sensor/barometer', 'POST', 'Atmospheric pressure readings', true),
('device.sensor.barometer.raw', '/sensor/batch', 'POST', 'Batch upload multiple sensor readings', false),
('device.sensor.temperature.raw', '/sensor/temperature', 'POST', 'Temperature sensor readings', true),
('device.sensor.temperature.raw', '/sensor/batch', 'POST', 'Batch upload multiple sensor readings', false);

-- Health endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.health.heartrate.raw', '/sensor/heartrate', 'POST', 'Heart rate measurements with confidence scores', true),
('device.health.heartrate.raw', '/health/heartrate', 'POST', 'Heart rate data via health endpoint', false),
('device.health.steps.raw', '/sensor/steps', 'POST', 'Step count data', true),
('device.health.steps.raw', '/health/steps', 'POST', 'Step count via health endpoint', false);

-- Power and system state
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.state.power.raw', '/sensor/power', 'POST', 'Device battery level and charging status', true);

-- OS Events endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('os.events.app_lifecycle.raw', '/os-events/app-lifecycle', 'POST', 'Android app lifecycle events (launch, foreground, background, terminate)', true),
('os.events.system.raw', '/os-events/system', 'POST', 'System events (screen on/off, lock/unlock, power connected/disconnected)', true),
('os.events.notifications.raw', '/os-events/notifications', 'POST', 'System notification events', true);

-- System monitoring endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.system.apps.android.raw', '/system/apps/android', 'POST', 'Android app monitoring data (running apps, PIDs, states)', true),
('device.system.apps.android.raw', '/system/apps/android/usage', 'POST', 'Android app usage statistics from UsageStats API', false),
('device.system.apps.macos.raw', '/system/apps/macos', 'POST', 'macOS app monitoring data', true),
('device.metadata.raw', '/system/metadata', 'POST', 'Device metadata and capabilities', true);

-- Network endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.network.wifi.raw', '/sensor/wifi', 'POST', 'WiFi connection state and signal strength', true),
('device.network.bluetooth.raw', '/sensor/bluetooth', 'POST', 'Nearby Bluetooth devices', true);

-- Digital data endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('digital.clipboard.raw', '/digital/clipboard', 'POST', 'Clipboard content changes', true),
('digital.web_analytics.raw', '/digital/web-analytics', 'POST', 'Website analytics data', true);

-- Image endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.image.camera.raw', '/images/upload', 'POST', 'Upload camera photos or images', true),
('device.image.screenshot.raw', '/images/screenshot', 'POST', 'Upload screenshots', true),
('device.video.screen.raw', '/images/upload', 'POST', 'Upload screen recording keyframes', false);

-- Document endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('digital.notes.raw', '/notes/upload', 'POST', 'Upload notes and text documents', true),
('digital.documents.raw', '/documents/upload', 'POST', 'Upload various document types', true);

-- URL processing endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('task.url.ingest', '/urls/submit', 'POST', 'Submit URLs for processing', true);

-- Unified ingestion endpoint (can route to multiple topics)
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description, is_primary) VALUES
('device.audio.raw', '/ingest', 'POST', 'Unified ingestion endpoint - audio data', false),
('device.sensor.gps.raw', '/ingest', 'POST', 'Unified ingestion endpoint - GPS data', false),
('device.sensor.accelerometer.raw', '/ingest', 'POST', 'Unified ingestion endpoint - accelerometer data', false),
('device.health.heartrate.raw', '/ingest', 'POST', 'Unified ingestion endpoint - heart rate data', false),
('device.image.camera.raw', '/ingest', 'POST', 'Unified ingestion endpoint - image data', false),
('device.system.apps.android.raw', '/ingest', 'POST', 'Unified ingestion endpoint - app monitoring', false),
('os.events.system.raw', '/ingest', 'POST', 'Unified ingestion endpoint - OS events', false);

-- Create views for easier querying

-- View: Topics with their primary endpoints
CREATE OR REPLACE VIEW v_topic_primary_endpoints AS
SELECT
    kt.topic_name,
    kt.category,
    kt.source,
    kt.datatype,
    tae.api_endpoint,
    tae.api_method,
    tae.api_description,
    kt.description as topic_description
FROM kafka_topics kt
LEFT JOIN topic_api_endpoints tae ON kt.topic_name = tae.topic_name AND tae.is_primary = true
WHERE kt.is_active = true
ORDER BY kt.category, kt.source, kt.datatype;

-- View: All endpoint mappings with details
CREATE OR REPLACE VIEW v_api_endpoint_mappings AS
SELECT
    tae.api_endpoint,
    tae.api_method,
    tae.topic_name,
    kt.category,
    kt.source,
    kt.datatype,
    tae.api_description,
    tae.is_primary,
    COUNT(*) OVER (PARTITION BY tae.api_endpoint) as topics_per_endpoint,
    COUNT(*) OVER (PARTITION BY tae.topic_name) as endpoints_per_topic
FROM topic_api_endpoints tae
JOIN kafka_topics kt ON tae.topic_name = kt.topic_name
WHERE kt.is_active = true
ORDER BY tae.api_endpoint, tae.topic_name;

-- View: Endpoints grouped by service/router
CREATE OR REPLACE VIEW v_endpoints_by_service AS
SELECT
    SPLIT_PART(api_endpoint, '/', 2) as service,
    COUNT(DISTINCT api_endpoint) as endpoint_count,
    COUNT(DISTINCT topic_name) as topic_count,
    array_agg(DISTINCT api_endpoint ORDER BY api_endpoint) as endpoints,
    array_agg(DISTINCT topic_name ORDER BY topic_name) as topics
FROM topic_api_endpoints
GROUP BY SPLIT_PART(api_endpoint, '/', 2)
ORDER BY service;

-- Function: Get all endpoints for a topic
CREATE OR REPLACE FUNCTION get_topic_endpoints(p_topic_name TEXT)
RETURNS TABLE(
    endpoint TEXT,
    method TEXT,
    description TEXT,
    is_primary BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tae.api_endpoint,
        tae.api_method,
        tae.api_description,
        tae.is_primary
    FROM topic_api_endpoints tae
    WHERE tae.topic_name = p_topic_name
    ORDER BY tae.is_primary DESC, tae.api_endpoint;
END;
$$ LANGUAGE plpgsql;

-- Function: Find topics by endpoint
CREATE OR REPLACE FUNCTION find_topics_by_endpoint(p_endpoint TEXT)
RETURNS TABLE(
    topic_name TEXT,
    category TEXT,
    method TEXT,
    description TEXT,
    is_primary BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        kt.topic_name,
        kt.category,
        tae.api_method,
        tae.api_description,
        tae.is_primary
    FROM topic_api_endpoints tae
    JOIN kafka_topics kt ON tae.topic_name = kt.topic_name
    WHERE tae.api_endpoint = p_endpoint
    ORDER BY kt.topic_name;
END;
$$ LANGUAGE plpgsql;

-- Function: Get API documentation for a topic
CREATE OR REPLACE FUNCTION get_topic_api_docs(p_topic_name TEXT)
RETURNS TABLE(
    endpoint TEXT,
    method TEXT,
    description TEXT,
    example_payload JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tae.api_endpoint,
        tae.api_method,
        tae.api_description,
        CASE
            WHEN kt.category = 'device' AND kt.datatype = 'gps' THEN
                '{"device_id": "uuid", "timestamp": "2024-01-01T00:00:00Z", "latitude": 36.1749, "longitude": -86.7678, "accuracy": 10.0}'::jsonb
            WHEN kt.category = 'device' AND kt.source = 'audio' THEN
                '{"device_id": "uuid", "timestamp": "2024-01-01T00:00:00Z", "audio_data": "base64_encoded_audio", "sample_rate": 16000}'::jsonb
            WHEN kt.category = 'device' AND kt.source = 'sensor' AND kt.datatype = 'accelerometer' THEN
                '{"device_id": "uuid", "timestamp": "2024-01-01T00:00:00Z", "x": 0.1, "y": -0.2, "z": 9.8}'::jsonb
            ELSE NULL
        END as example_payload
    FROM topic_api_endpoints tae
    JOIN kafka_topics kt ON tae.topic_name = kt.topic_name
    WHERE tae.topic_name = p_topic_name
    ORDER BY tae.is_primary DESC, tae.api_endpoint;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE topic_api_endpoints IS 'Mapping of Kafka topics to their FastAPI ingestion endpoints';
COMMENT ON COLUMN topic_api_endpoints.is_primary IS 'Indicates if this is the primary/recommended endpoint for the topic';
COMMENT ON VIEW v_topic_primary_endpoints IS 'Topics with their primary API endpoints';
COMMENT ON VIEW v_api_endpoint_mappings IS 'Complete mapping of all API endpoints to Kafka topics';
COMMENT ON VIEW v_endpoints_by_service IS 'API endpoints grouped by service/router prefix';
COMMENT ON FUNCTION get_topic_endpoints IS 'Get all API endpoints that can produce data for a specific topic';
COMMENT ON FUNCTION find_topics_by_endpoint IS 'Find all topics that can receive data from a specific API endpoint';
COMMENT ON FUNCTION get_topic_api_docs IS 'Get API documentation and example payloads for a topic';
