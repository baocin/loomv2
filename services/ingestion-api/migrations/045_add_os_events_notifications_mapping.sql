-- Add missing database mapping for OS notifications events
-- This ensures kafka-to-db-consumer knows how to process notification events

-- First, add the topic to table mapping if it doesn't exist
INSERT INTO kafka_topic_table_mappings (topic, table_name, unique_columns, conflict_resolution)
VALUES ('os.events.notifications.raw', 'os_events_notifications_raw', 'device_id, timestamp, notification_id', 'ignore')
ON CONFLICT (topic) DO NOTHING;

-- Add field mappings for notification events
INSERT INTO kafka_topic_field_mappings (topic, table_name, kafka_field, db_column, data_type, is_required)
VALUES
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'device_id', 'device_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'timestamp', 'timestamp', 'timestamp', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'schema_version', 'schema_version', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'notification_id', 'notification_id', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'event_type', 'event_type', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'package_name', 'package_name', 'string', true),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'app_name', 'app_name', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'title', 'title', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'text', 'text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'subtext', 'subtext', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'big_text', 'big_text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'info_text', 'info_text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'summary_text', 'summary_text', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'category', 'category', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'priority', 'priority', 'integer', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'visibility', 'visibility', 'integer', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'color', 'color', 'integer', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'is_ongoing', 'is_ongoing', 'boolean', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'is_clearable', 'is_clearable', 'boolean', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'is_group', 'is_group', 'boolean', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'group_key', 'group_key', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'posted_time', 'posted_time', 'timestamp', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'when_time', 'when_time', 'timestamp', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'created_at', 'created_at', 'timestamp', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'trace_id', 'trace_id', 'string', false),
    ('os.events.notifications.raw', 'os_events_notifications_raw', 'duration_ms', 'duration_ms', 'integer', false)
ON CONFLICT (topic, table_name, kafka_field) DO NOTHING;
