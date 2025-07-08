-- Fix OS events field mappings
-- The issue is that the consumer is trying to insert trace_id into the id column
-- We need to ensure that the id column is not mapped from any Kafka field

-- First, remove any mappings that target the id column for OS events
DELETE FROM topic_field_mappings
WHERE topic_name IN ('os.events.system.raw', 'os.events.app_lifecycle.raw', 'os.events.notifications.raw')
AND target_column = 'id';

-- Add explicit mappings for all required fields (without id)
-- For system events
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.system.raw', 'os_events_system_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.system.raw', 'os_events_system_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'event_category', 'event_category', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'severity', 'severity', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'description', 'description', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'metadata', 'metadata', 'jsonb', false),
    ('os.events.system.raw', 'os_events_system_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'trace_id', 'trace_id', 'string', false)
ON CONFLICT (topic_name, table_name, source_field_path) DO UPDATE SET
    target_column = EXCLUDED.target_column,
    data_type = EXCLUDED.data_type,
    is_required = EXCLUDED.is_required;

-- For app lifecycle events
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_identifier', 'app_identifier', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_name', 'app_name', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'duration_seconds', 'duration_seconds', 'integer', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'metadata', 'metadata', 'jsonb', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'trace_id', 'trace_id', 'string', false)
ON CONFLICT (topic_name, table_name, source_field_path) DO UPDATE SET
    target_column = EXCLUDED.target_column,
    data_type = EXCLUDED.data_type,
    is_required = EXCLUDED.is_required;

-- For notification events
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'notification_id', 'notification_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'app_identifier', 'app_identifier', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'title', 'title', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'text', 'text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'action', 'action', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'body', 'body', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'metadata', 'metadata', 'jsonb', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'trace_id', 'trace_id', 'string', false)
ON CONFLICT (topic_name, table_name, source_field_path) DO UPDATE SET
    target_column = EXCLUDED.target_column,
    data_type = EXCLUDED.data_type,
    is_required = EXCLUDED.is_required;

-- Clean up any duplicate or old mappings
DELETE FROM topic_field_mappings
WHERE topic_name IN ('os.events.system.raw', 'os.events.app_lifecycle.raw', 'os.events.notifications.raw')
AND source_field_path LIKE 'data.%';
