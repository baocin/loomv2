-- Migration 032: Insert Initial Georegion Data
-- Description: Inserts default georegion definitions for common locations

-- Clear existing default data (if any)
DELETE FROM georegions WHERE name IN ('Home', 'Work', 'Gym');

-- Insert initial georegions with realistic San Francisco locations
INSERT INTO georegions (name, description, center_latitude, center_longitude, radius_meters, type, metadata) VALUES
    -- Home location (example: Mission District, San Francisco)
    ('Home', 'Primary residence', 37.7599, -122.4148, 100, 'home', 
     '{"address": "Mission District, San Francisco, CA", "notes": "Default home location - update with actual coordinates"}'),
    
    -- Work location (example: Financial District, San Francisco)
    ('Work', 'Primary workplace', 37.7955, -122.3937, 150, 'work',
     '{"address": "Financial District, San Francisco, CA", "notes": "Default work location - update with actual coordinates"}'),
    
    -- Example custom locations
    ('Gym', 'Fitness center', 37.7851, -122.4056, 50, 'custom',
     '{"address": "SOMA, San Francisco, CA", "category": "fitness"}'),
    
    ('Coffee Shop', 'Favorite coffee shop', 37.7644, -122.4199, 30, 'custom',
     '{"address": "Valencia Street, San Francisco, CA", "category": "food_drink"}'),
    
    ('Grocery Store', 'Regular grocery shopping', 37.7609, -122.4138, 75, 'custom',
     '{"address": "Mission District, San Francisco, CA", "category": "shopping"}'),
    
    ('Park', 'Dolores Park', 37.7596, -122.4269, 200, 'custom',
     '{"address": "Dolores Park, San Francisco, CA", "category": "recreation"}'
    );

-- Note: These are example locations in San Francisco. 
-- Users should update these with their actual locations using:
-- UPDATE georegions SET center_latitude = ?, center_longitude = ?, radius_meters = ? WHERE name = ?;