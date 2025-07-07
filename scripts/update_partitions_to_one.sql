-- Simple script to update all topics to 1 partition
BEGIN;

-- Update all active topics to have 1 partition
UPDATE kafka_topics
SET 
    partitions = 1,
    updated_at = NOW()
WHERE is_active = true;

-- Show what was updated
SELECT 
    topic_name,
    partitions,
    category,
    updated_at
FROM kafka_topics
WHERE is_active = true
  AND topic_name IN (
    'device.audio.raw',
    'device.sensor.accelerometer.raw',
    'os.events.app_lifecycle.raw', 
    'os.events.system.raw',
    'media.audio.vad_filtered'
  )
ORDER BY topic_name;

COMMIT;