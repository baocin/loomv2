-- Migration 033: Add Polygon Georegion Support
-- Description: Adds support for storing polygon geometries and advanced georegion shapes

-- Add polygon_coordinates column to store the original polygon data
ALTER TABLE georegions 
ADD COLUMN IF NOT EXISTS polygon_coordinates JSONB;

-- Add a column to store the geometry type
ALTER TABLE georegions
ADD COLUMN IF NOT EXISTS geometry_type TEXT DEFAULT 'circle' CHECK (geometry_type IN ('circle', 'polygon'));

-- Update the Home location with its full polygon coordinates
UPDATE georegions 
SET 
    polygon_coordinates = '{
        "type": "Polygon",
        "coordinates": [[
            [-86.685127, 36.046366],
            [-86.682296, 36.047976],
            [-86.683277, 36.048782],
            [-86.686243, 36.047234],
            [-86.685127, 36.046366]
        ]]
    }'::jsonb,
    geometry_type = 'polygon',
    metadata = jsonb_set(
        metadata,
        '{original_geojson}',
        '{
            "type": "Feature",
            "properties": {
                "id": 2609,
                "shape": "Polygon"
            }
        }'::jsonb
    )
WHERE name = 'Home';

-- Add an index on geometry_type for faster queries
CREATE INDEX IF NOT EXISTS idx_georegions_geometry_type ON georegions(geometry_type);

-- Create a function to check if a point is within a polygon (simplified version)
-- This is a basic point-in-polygon algorithm that doesn't require PostGIS
CREATE OR REPLACE FUNCTION point_in_polygon(
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    polygon_coords JSONB
) RETURNS BOOLEAN AS $$
DECLARE
    coords JSONB;
    n INT;
    p1x DOUBLE PRECISION;
    p1y DOUBLE PRECISION;
    p2x DOUBLE PRECISION;
    p2y DOUBLE PRECISION;
    inside BOOLEAN := FALSE;
    i INT;
BEGIN
    -- Extract the first ring of coordinates
    coords := polygon_coords->'coordinates'->0;
    n := jsonb_array_length(coords);
    
    -- Ray casting algorithm
    FOR i IN 0..(n-1) LOOP
        p1x := (coords->i->0)::DOUBLE PRECISION;
        p1y := (coords->i->1)::DOUBLE PRECISION;
        p2x := (coords->((i+1) % n)->0)::DOUBLE PRECISION;
        p2y := (coords->((i+1) % n)->1)::DOUBLE PRECISION;
        
        IF ((p1y > lat) != (p2y > lat)) AND 
           (lon < (p2x - p1x) * (lat - p1y) / (p2y - p1y) + p1x) THEN
            inside := NOT inside;
        END IF;
    END LOOP;
    
    RETURN inside;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create a view for easier georegion detection that handles both circles and polygons
CREATE OR REPLACE VIEW georegion_detection_view AS
SELECT
    id,
    name,
    description,
    center_latitude,
    center_longitude,
    radius_meters,
    type,
    geometry_type,
    polygon_coordinates,
    is_active,
    metadata
FROM georegions
WHERE is_active = TRUE;

-- Add comment explaining the polygon support
COMMENT ON COLUMN georegions.polygon_coordinates IS 'GeoJSON polygon coordinates for polygon-type georegions';
COMMENT ON COLUMN georegions.geometry_type IS 'Type of geometry: circle (uses center+radius) or polygon (uses polygon_coordinates)';
COMMENT ON FUNCTION point_in_polygon IS 'Simple point-in-polygon test without PostGIS dependency';