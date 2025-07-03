# Georegion Detection

Georegions allow you to define important locations (home, work, custom places) and track when devices enter, exit, or dwell in these areas.

## Database Schema

### Tables

1. **`georegions`** - Stores georegion definitions
   - `id`: Unique identifier
   - `name`: Human-readable name (e.g., "Home", "Work", "Gym")
   - `type`: Category ('home', 'work', 'custom')
   - `center_latitude/longitude`: Center coordinates
   - `radius_meters`: Detection radius
   - `is_active`: Enable/disable tracking

2. **`location_georegion_detected`** - Stores detection events
   - Records when devices enter/exit/dwell in georegions
   - Includes confidence scores and dwell time
   - Links to source GPS data

3. **`location_address_geocoded`** - Stores geocoded addresses
   - Converts GPS coordinates to human-readable addresses
   - Caches results from geocoding services

## Default Georegions

The system comes with example georegions in San Francisco:
- **Home**: Mission District (37.7599, -122.4148)
- **Work**: Financial District (37.7955, -122.3937)
- **Gym**: SOMA area example
- **Coffee Shop**: Valencia Street example
- **Grocery Store**: Mission area example
- **Park**: Dolores Park

## Managing Georegions

### Update Your Locations

```sql
-- Update home location
UPDATE georegions 
SET center_latitude = YOUR_LAT, 
    center_longitude = YOUR_LON, 
    radius_meters = 100 
WHERE name = 'Home';

-- Update work location
UPDATE georegions 
SET center_latitude = YOUR_LAT, 
    center_longitude = YOUR_LON, 
    radius_meters = 150 
WHERE name = 'Work';
```

### Add Custom Locations

```sql
INSERT INTO georegions (name, description, center_latitude, center_longitude, radius_meters, type) 
VALUES ('Parents House', 'Parents home', 37.8044, -122.2711, 100, 'custom');
```

### View Detection Events

```sql
-- Recent detections
SELECT * FROM location_georegion_detected 
ORDER BY timestamp DESC 
LIMIT 20;

-- Time spent in each location today
SELECT 
    georegion_name,
    SUM(dwell_time_seconds) / 3600.0 as hours
FROM location_georegion_detected
WHERE timestamp >= CURRENT_DATE
    AND event_type = 'dwell'
GROUP BY georegion_name;
```

## Kafka Topics

- **Input**: `device.sensor.gps.raw` - Raw GPS data
- **Output**: `location.georegion.detected` - Detection events

## Detection Logic

The georegion detection service:
1. Consumes GPS data from Kafka
2. Checks if coordinates fall within any active georegion
3. Tracks state transitions (enter/exit)
4. Calculates dwell time for continuous presence
5. Publishes detection events to Kafka

## Privacy Considerations

- Georegion definitions are stored locally
- Detection happens on-premises
- No location data is sent to external services
- Users control which georegions are active
- Detection radius can be adjusted for privacy/accuracy trade-off