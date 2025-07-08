-- Fix JSON serialization for OS events metadata fields
-- Update the metadata field mappings to include json_stringify transformation

UPDATE topic_field_mappings
SET transformation = 'json_stringify'
WHERE topic_name IN ('os.events.system.raw', 'os.events.app_lifecycle.raw', 'os.events.notifications.raw')
AND target_column = 'metadata';
