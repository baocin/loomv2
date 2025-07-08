-- Fix notification events by removing all mappings and recreating clean ones
DELETE FROM topic_field_mappings WHERE topic_name = 'os.events.notifications.raw';

-- Add correct notification mappings
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'notification_id', 'notification_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'app_identifier', 'app_identifier', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'title', 'title', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'text', 'text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'body', 'body', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'action', 'action', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'metadata', 'metadata', 'json', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'trace_id', 'trace_id', 'string', false);

-- Add json_stringify transformation for metadata
UPDATE topic_field_mappings
SET transformation = 'json_stringify'
WHERE topic_name = 'os.events.notifications.raw' AND target_column = 'metadata';
