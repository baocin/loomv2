-- Final fix for OS events mappings
-- 1. Remove all old/incorrect mappings
-- 2. Add correct mappings with proper data types

-- Clean up ALL old mappings for OS events
DELETE FROM topic_field_mappings
WHERE topic_name IN ('os.events.system.raw', 'os.events.app_lifecycle.raw', 'os.events.notifications.raw');

-- System events mappings
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.system.raw', 'os_events_system_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.system.raw', 'os_events_system_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.system.raw', 'os_events_system_raw', 'event_category', 'event_category', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'severity', 'severity', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'description', 'description', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'metadata', 'metadata', 'json', false),  -- Changed to json
    ('os.events.system.raw', 'os_events_system_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.system.raw', 'os_events_system_raw', 'trace_id', 'trace_id', 'string', false);

-- App lifecycle events mappings
INSERT INTO topic_field_mappings (topic_name, table_name, source_field_path, target_column, data_type, is_required)
VALUES
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_identifier', 'app_identifier', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'app_name', 'app_name', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'duration_seconds', 'duration_seconds', 'integer', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'metadata', 'metadata', 'json', false),  -- Changed to json
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.app_lifecycle.raw', 'os_events_app_lifecycle_raw', 'trace_id', 'trace_id', 'string', false);

-- Notification events mappings (without data. prefix)
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
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'metadata', 'metadata', 'json', false),  -- Changed to json
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'trace_id', 'trace_id', 'string', false);
