-- Add missing API endpoint to topic mappings
-- These mappings connect the Ingestion API endpoints to their corresponding Kafka topics

-- Add missing image/video endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.image.camera.raw', '/images/upload', 'POST', 'Upload camera images')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.image.screenshot.raw', '/images/screenshot', 'POST', 'Upload screenshots')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.video.screen.raw', '/images/video', 'POST', 'Upload video recordings')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add missing sensor endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.sensor.temperature.raw', '/sensor/temperature', 'POST', 'Temperature sensor data')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.sensor.barometer.raw', '/sensor/barometer', 'POST', 'Barometric pressure data')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.network.wifi.raw', '/sensor/wifi', 'POST', 'WiFi network status')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.network.bluetooth.raw', '/sensor/bluetooth', 'POST', 'Bluetooth device status')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add missing health endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.health.steps.raw', '/health/steps', 'POST', 'Step count data')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add missing system endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.system.apps.macos.raw', '/system/apps/macos', 'POST', 'macOS application monitoring')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.metadata.raw', '/system/metadata', 'POST', 'Device metadata information')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add missing digital endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('digital.clipboard.raw', '/digital/clipboard', 'POST', 'Clipboard content')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('digital.web_analytics.raw', '/digital/web-analytics', 'POST', 'Web browsing analytics')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('digital.notes.raw', '/notes/upload', 'POST', 'Text notes and memos')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('digital.documents.raw', '/documents/upload', 'POST', 'Document uploads')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add OS event endpoints
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('os.events.notifications.raw', '/os-events/notifications', 'POST', 'System notifications')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Add existing endpoints for completeness
INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.audio.raw', '/audio/upload', 'POST', 'Audio file upload')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.audio.raw', '/audio/stream/{device_id}', 'WEBSOCKET', 'Audio WebSocket streaming')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.sensor.gps.raw', '/sensor/gps', 'POST', 'GPS location data')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.sensor.accelerometer.raw', '/sensor/accelerometer', 'POST', 'Accelerometer motion data')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.health.heartrate.raw', '/sensor/heartrate', 'POST', 'Heart rate measurements')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.state.power.raw', '/sensor/power', 'POST', 'Device power state')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('os.events.app_lifecycle.raw', '/os-events/app-lifecycle', 'POST', 'App lifecycle events')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('os.events.system.raw', '/os-events/system', 'POST', 'System events (screen, lock, power)')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.system.apps.android.raw', '/system/apps/android', 'POST', 'Android app monitoring')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

INSERT INTO topic_api_endpoints (topic_name, api_endpoint, api_method, api_description) VALUES
('device.system.apps.android.raw', '/system/apps/android/usage', 'POST', 'Android app usage stats')
ON CONFLICT (topic_name, api_endpoint, api_method) DO NOTHING;

-- Display the mappings
SELECT topic_name, api_endpoint, api_method, api_description
FROM topic_api_endpoints
ORDER BY api_endpoint;
