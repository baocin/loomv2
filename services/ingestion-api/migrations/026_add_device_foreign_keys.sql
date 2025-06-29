-- Migration 026: Add Device Foreign Keys
-- Description: Adds foreign key constraints from data tables to devices table
-- This ensures referential integrity and enables cascade operations

-- Note: Adding foreign keys to hypertables requires special handling
-- We'll add them without CASCADE DELETE to avoid issues with TimescaleDB

-- Function to safely add foreign key constraints
CREATE OR REPLACE FUNCTION add_device_foreign_key(
    table_name TEXT,
    column_name TEXT DEFAULT 'device_id'
) RETURNS void AS $$
DECLARE
    constraint_name TEXT;
BEGIN
    constraint_name := table_name || '_' || column_name || '_fkey';
    
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = constraint_name
    ) THEN
        -- Add foreign key with ON DELETE SET NULL instead of CASCADE
        -- This is safer for TimescaleDB hypertables
        EXECUTE format(
            'ALTER TABLE %I ADD CONSTRAINT %I 
             FOREIGN KEY (%I) REFERENCES devices(device_id) 
             ON DELETE SET NULL ON UPDATE CASCADE',
            table_name, constraint_name, column_name
        );
        RAISE NOTICE 'Added foreign key constraint % to table %', constraint_name, table_name;
    ELSE
        RAISE NOTICE 'Foreign key constraint % already exists on table %', constraint_name, table_name;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't fail the migration
        RAISE WARNING 'Could not add foreign key to %: %', table_name, SQLERRM;
END;
$$ LANGUAGE plpgsql;

-- Add foreign keys to device data tables
-- Note: We're being selective here - only tables that definitely use device_id
SELECT add_device_foreign_key('device_audio_raw');
SELECT add_device_foreign_key('device_sensor_gps_raw');
SELECT add_device_foreign_key('device_sensor_accelerometer_raw');
SELECT add_device_foreign_key('device_sensor_generic_raw');
SELECT add_device_foreign_key('device_health_heartrate_raw');
SELECT add_device_foreign_key('device_state_power_raw');
SELECT add_device_foreign_key('device_image_camera_raw');
SELECT add_device_foreign_key('device_text_notes_raw');
SELECT add_device_foreign_key('digital_clipboard_raw');
SELECT add_device_foreign_key('digital_web_analytics_raw');

-- For tables that might have NULL device_id, we handle them differently
-- These are typically external data sources
SELECT add_device_foreign_key('external_twitter_liked_raw');
SELECT add_device_foreign_key('external_calendar_events_raw');
SELECT add_device_foreign_key('external_email_events_raw');

-- Create trigger to auto-register unknown devices
CREATE OR REPLACE FUNCTION auto_register_device_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Only process if device_id is not null and device doesn't exist
    IF NEW.device_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM devices WHERE device_id = NEW.device_id
    ) THEN
        -- Auto-register the device
        PERFORM auto_register_device(
            NEW.device_id,
            CASE 
                WHEN NEW.device_id LIKE '%-fetcher-%' THEN 'service_fetcher'
                WHEN NEW.device_id LIKE '%-consumer-%' THEN 'service_consumer'
                WHEN NEW.device_id LIKE 'android-%' THEN 'mobile_android'
                WHEN NEW.device_id LIKE 'ios-%' THEN 'mobile_ios'
                WHEN NEW.device_id LIKE 'macos-%' THEN 'desktop_macos'
                WHEN NEW.device_id LIKE 'linux-%' THEN 'desktop_linux'
                WHEN NEW.device_id LIKE 'windows-%' THEN 'desktop_windows'
                ELSE 'other'
            END,
            jsonb_build_object(
                'auto_registered', true,
                'first_seen_table', TG_TABLE_NAME,
                'first_seen_at', NOW()
            )
        );
    END IF;
    
    -- Update last_seen_at for existing devices
    IF NEW.device_id IS NOT NULL THEN
        UPDATE devices 
        SET last_seen_at = NOW() 
        WHERE device_id = NEW.device_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add auto-registration triggers to main ingestion tables
-- We'll add these to tables that frequently receive new device data
CREATE TRIGGER auto_register_device_audio
    BEFORE INSERT ON device_audio_raw
    FOR EACH ROW
    EXECUTE FUNCTION auto_register_device_trigger();

CREATE TRIGGER auto_register_device_sensor
    BEFORE INSERT ON device_sensor_gps_raw
    FOR EACH ROW
    EXECUTE FUNCTION auto_register_device_trigger();

-- Add device management functions
CREATE OR REPLACE FUNCTION update_device_name(
    p_device_id TEXT,
    p_new_name TEXT
) RETURNS void AS $$
BEGIN
    UPDATE devices 
    SET name = p_new_name,
        updated_at = NOW()
    WHERE device_id = p_device_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Device % not found', p_device_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to merge duplicate devices
CREATE OR REPLACE FUNCTION merge_devices(
    p_old_device_id TEXT,
    p_new_device_id TEXT
) RETURNS void AS $$
BEGIN
    -- Update all data tables to use new device_id
    UPDATE device_audio_raw SET device_id = p_new_device_id WHERE device_id = p_old_device_id;
    UPDATE device_sensor_gps_raw SET device_id = p_new_device_id WHERE device_id = p_old_device_id;
    UPDATE device_sensor_accelerometer_raw SET device_id = p_new_device_id WHERE device_id = p_old_device_id;
    -- Add more tables as needed
    
    -- Delete old device record
    DELETE FROM devices WHERE device_id = p_old_device_id;
    
    -- Update last_seen on new device
    UPDATE devices SET last_seen_at = NOW() WHERE device_id = p_new_device_id;
END;
$$ LANGUAGE plpgsql;

-- Create helpful views
CREATE OR REPLACE VIEW device_data_summary AS
SELECT 
    d.device_id,
    d.name,
    d.device_type,
    COUNT(DISTINCT da.id) as audio_records,
    COUNT(DISTINCT dg.id) as gps_records,
    COUNT(DISTINCT ds.id) as sensor_records,
    MIN(LEAST(da.timestamp, dg.timestamp, ds.timestamp)) as earliest_data,
    MAX(GREATEST(da.timestamp, dg.timestamp, ds.timestamp)) as latest_data
FROM devices d
LEFT JOIN device_audio_raw da ON d.device_id = da.device_id
LEFT JOIN device_sensor_gps_raw dg ON d.device_id = dg.device_id
LEFT JOIN device_sensor_accelerometer_raw ds ON d.device_id = ds.device_id
GROUP BY d.device_id, d.name, d.device_type;

-- Add comments
COMMENT ON FUNCTION auto_register_device IS 'Automatically registers a new device when data is received';
COMMENT ON FUNCTION update_device_name IS 'Updates the human-readable name for a device';
COMMENT ON FUNCTION merge_devices IS 'Merges data from one device_id to another (useful for handling device resets)';