-- Migration 032: Insert Initial Georegion Data
-- Description: Inserts initial home georegion

-- Clear existing default data (if any)
DELETE FROM georegions WHERE name = 'Home';

-- Insert home georegion (Nashville location from provided GeoJSON)
-- Center calculated as average of polygon coordinates
-- Approximate radius based on polygon dimensions
INSERT INTO georegions (name, description, center_latitude, center_longitude, radius_meters, type, metadata) VALUES
    ('Home', 'Primary residence', 36.047644, -86.684133, 150, 'home',
     '{"address": "Nashville, TN", "polygon_id": 2609, "original_geometry": "polygon", "notes": "Location from GeoJSON feature ID 2609"}'
    );