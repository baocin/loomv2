-- Georegion Management Script
-- This script provides helpful queries for managing georegions in Loom v2

-- View all georegions
SELECT id, name, type, description, center_latitude, center_longitude, radius_meters, is_active
FROM georegions
ORDER BY type, name;

-- Update home location (replace with your actual coordinates)
-- Example: UPDATE georegions SET center_latitude = 37.7749, center_longitude = -122.4194, radius_meters = 100 WHERE name = 'Home';

-- Update work location (replace with your actual coordinates)
-- Example: UPDATE georegions SET center_latitude = 37.7955, center_longitude = -122.3937, radius_meters = 150 WHERE name = 'Work';

-- Add a new custom georegion
-- Example: INSERT INTO georegions (name, description, center_latitude, center_longitude, radius_meters, type) 
-- VALUES ('Parents House', 'Parents home', 37.8044, -122.2711, 100, 'custom');

-- Disable a georegion (stop tracking it)
-- Example: UPDATE georegions SET is_active = false WHERE name = 'Gym';

-- View recent georegion detections
SELECT 
    lgd.timestamp,
    lgd.device_id,
    lgd.georegion_name,
    lgd.event_type,
    lgd.distance_from_center_meters,
    lgd.dwell_time_seconds
FROM location_georegion_detected lgd
ORDER BY lgd.timestamp DESC
LIMIT 20;

-- View time spent in each georegion today
SELECT 
    georegion_name,
    georegion_type,
    COUNT(*) as event_count,
    SUM(CASE WHEN event_type = 'dwell' THEN dwell_time_seconds ELSE 0 END) as total_dwell_seconds,
    SUM(CASE WHEN event_type = 'dwell' THEN dwell_time_seconds ELSE 0 END) / 3600.0 as total_dwell_hours
FROM location_georegion_detected
WHERE timestamp >= CURRENT_DATE
GROUP BY georegion_name, georegion_type
ORDER BY total_dwell_seconds DESC;

-- Find georegions near a specific location (within 1km)
-- Replace lat/lon with your coordinates
-- Example: Find georegions near (37.7749, -122.4194)
SELECT 
    name,
    type,
    center_latitude,
    center_longitude,
    radius_meters,
    -- Haversine formula for distance calculation (in meters)
    6371000 * acos(
        cos(radians(37.7749)) * cos(radians(center_latitude)) * 
        cos(radians(center_longitude) - radians(-122.4194)) + 
        sin(radians(37.7749)) * sin(radians(center_latitude))
    ) as distance_meters
FROM georegions
WHERE is_active = true
HAVING distance_meters < 1000
ORDER BY distance_meters;

-- View georegion entry/exit patterns for the last 7 days
SELECT 
    DATE(timestamp) as date,
    georegion_name,
    event_type,
    COUNT(*) as event_count
FROM location_georegion_detected
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp), georegion_name, event_type
ORDER BY date DESC, georegion_name, event_type;