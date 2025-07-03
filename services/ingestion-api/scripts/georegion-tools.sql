-- Georegion Management Tools
-- Helpful SQL queries and functions for working with georegions

-- 1. View all georegions with their types
SELECT 
    id,
    name,
    description,
    geometry_type,
    CASE 
        WHEN geometry_type = 'circle' THEN 
            format('Circle: center(%s, %s) radius=%sm', center_latitude, center_longitude, radius_meters)
        WHEN geometry_type = 'polygon' THEN 
            format('Polygon with %s vertices', jsonb_array_length(polygon_coordinates->'coordinates'->0))
    END as geometry_info,
    type,
    is_active
FROM georegions
ORDER BY type, name;

-- 2. Test if a specific GPS coordinate is within any georegion
-- Example: Check if coordinate (36.047500, -86.684000) is in any georegion
WITH test_point AS (
    SELECT 36.047500 as lat, -86.684000 as lon
)
SELECT 
    g.name,
    g.type,
    g.geometry_type,
    CASE 
        WHEN g.geometry_type = 'circle' THEN
            -- Haversine formula for circle detection
            (6371000 * acos(
                cos(radians(tp.lat)) * cos(radians(g.center_latitude)) *
                cos(radians(g.center_longitude) - radians(tp.lon)) +
                sin(radians(tp.lat)) * sin(radians(g.center_latitude))
            )) <= g.radius_meters
        WHEN g.geometry_type = 'polygon' THEN
            point_in_polygon(tp.lat, tp.lon, g.polygon_coordinates)
    END as is_within
FROM georegions g, test_point tp
WHERE g.is_active = TRUE;

-- 3. Calculate the bounding box of a polygon georegion
SELECT 
    name,
    geometry_type,
    CASE 
        WHEN geometry_type = 'polygon' AND polygon_coordinates IS NOT NULL THEN
            jsonb_build_object(
                'min_lat', (
                    SELECT MIN((coord->1)::float)
                    FROM jsonb_array_elements(polygon_coordinates->'coordinates'->0) as coord
                ),
                'max_lat', (
                    SELECT MAX((coord->1)::float)
                    FROM jsonb_array_elements(polygon_coordinates->'coordinates'->0) as coord
                ),
                'min_lon', (
                    SELECT MIN((coord->0)::float)
                    FROM jsonb_array_elements(polygon_coordinates->'coordinates'->0) as coord
                ),
                'max_lon', (
                    SELECT MAX((coord->0)::float)
                    FROM jsonb_array_elements(polygon_coordinates->'coordinates'->0) as coord
                )
            )
        ELSE NULL
    END as bounding_box
FROM georegions
WHERE geometry_type = 'polygon';

-- 4. Convert the Home polygon to Well-Known Text (WKT) format for visualization
-- This can be used with tools like geojson.io or QGIS
SELECT 
    name,
    format('POLYGON((%s))', 
        string_agg(
            format('%s %s', coord->0, coord->1), 
            ', ' 
            ORDER BY idx
        )
    ) as wkt
FROM georegions,
     jsonb_array_elements(polygon_coordinates->'coordinates'->0) WITH ORDINALITY as coords(coord, idx)
WHERE name = 'Home'
GROUP BY name, polygon_coordinates;

-- 5. Function to add a new circular georegion
CREATE OR REPLACE FUNCTION add_circular_georegion(
    p_name TEXT,
    p_description TEXT,
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION,
    p_radius_meters INTEGER,
    p_type TEXT DEFAULT 'custom'
) RETURNS INTEGER AS $$
DECLARE
    new_id INTEGER;
BEGIN
    INSERT INTO georegions (
        name, description, center_latitude, center_longitude, 
        radius_meters, type, geometry_type
    ) VALUES (
        p_name, p_description, p_latitude, p_longitude, 
        p_radius_meters, p_type, 'circle'
    ) RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Function to add a new polygon georegion from GeoJSON
CREATE OR REPLACE FUNCTION add_polygon_georegion(
    p_name TEXT,
    p_description TEXT,
    p_geojson JSONB,
    p_type TEXT DEFAULT 'custom'
) RETURNS INTEGER AS $$
DECLARE
    new_id INTEGER;
    center_lat DOUBLE PRECISION;
    center_lon DOUBLE PRECISION;
    approx_radius INTEGER;
BEGIN
    -- Calculate center point (centroid)
    SELECT 
        AVG((coord->1)::float),
        AVG((coord->0)::float)
    INTO center_lat, center_lon
    FROM jsonb_array_elements(p_geojson->'coordinates'->0) as coord;
    
    -- Calculate approximate radius (distance from center to furthest point)
    SELECT MAX(
        6371000 * acos(
            cos(radians(center_lat)) * cos(radians((coord->1)::float)) *
            cos(radians((coord->0)::float) - radians(center_lon)) +
            sin(radians(center_lat)) * sin(radians((coord->1)::float))
        )
    )::INTEGER
    INTO approx_radius
    FROM jsonb_array_elements(p_geojson->'coordinates'->0) as coord;
    
    INSERT INTO georegions (
        name, description, center_latitude, center_longitude, 
        radius_meters, type, geometry_type, polygon_coordinates
    ) VALUES (
        p_name, p_description, center_lat, center_lon, 
        approx_radius, p_type, 'polygon', p_geojson
    ) RETURNING id INTO new_id;
    
    RETURN new_id;
END;
$$ LANGUAGE plpgsql;

-- 7. Example: Add a new polygon georegion
-- SELECT add_polygon_georegion(
--     'My Custom Area',
--     'Description of the area',
--     '{
--         "type": "Polygon",
--         "coordinates": [[
--             [-86.685127, 36.046366],
--             [-86.682296, 36.047976],
--             [-86.683277, 36.048782],
--             [-86.686243, 36.047234],
--             [-86.685127, 36.046366]
--         ]]
--     }'::jsonb,
--     'custom'
-- );

-- 8. View recent georegion detections
SELECT 
    lgd.event_type,
    lgd.detected_at,
    lgd.dwell_time_seconds,
    g.name as georegion_name,
    g.type as georegion_type,
    lgd.device_id,
    lgd.confidence
FROM location_georegion_detected lgd
JOIN georegions g ON lgd.georegion_id = g.id
WHERE lgd.detected_at > NOW() - INTERVAL '24 hours'
ORDER BY lgd.detected_at DESC
LIMIT 100;