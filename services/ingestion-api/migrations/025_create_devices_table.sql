-- Migration 025: Create Devices Table
-- Description: Creates a devices table for managing device aliases and metadata
-- This allows mapping device_ids to human-readable names and tracking data sources

-- Create devices table
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    device_type TEXT NOT NULL CHECK (device_type IN (
        'mobile_android',
        'mobile_ios', 
        'desktop_macos',
        'desktop_linux',
        'desktop_windows',
        'service_scheduler',
        'service_fetcher',
        'service_consumer',
        'browser_extension',
        'other'
    )),
    platform TEXT,
    model TEXT,
    manufacturer TEXT,
    os_version TEXT,
    app_version TEXT,
    -- Service-specific fields
    service_name TEXT, -- For scheduled consumers/fetchers (e.g., 'email-fetcher', 'x-likes-fetcher')
    service_config JSONB, -- Service configuration (e.g., email accounts, fetch intervals)
    -- Metadata
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_devices_service ON devices(service_name) WHERE service_name IS NOT NULL;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_devices_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER devices_updated_at_trigger
    BEFORE UPDATE ON devices
    FOR EACH ROW
    EXECUTE FUNCTION update_devices_updated_at();

-- Insert default service devices
INSERT INTO devices (device_id, name, device_type, service_name, metadata) VALUES
    -- Email fetchers (one per account)
    ('email-fetcher-account-1', 'Primary Email Fetcher', 'service_fetcher', 'email-fetcher', 
     '{"account": "account_1", "description": "Primary email account sync"}'),
    ('email-fetcher-account-2', 'Secondary Email Fetcher', 'service_fetcher', 'email-fetcher',
     '{"account": "account_2", "description": "Secondary email account sync"}'),
    
    -- Social media fetchers
    ('x-likes-fetcher-default', 'X/Twitter Likes Fetcher', 'service_fetcher', 'x-likes-fetcher',
     '{"description": "Fetches liked tweets from X.com"}'),
    
    -- Calendar fetchers (one per calendar)
    ('calendar-fetcher-primary', 'Primary Calendar Sync', 'service_fetcher', 'calendar-fetcher',
     '{"calendar": "primary", "description": "Primary calendar sync"}'),
    ('calendar-fetcher-work', 'Work Calendar Sync', 'service_fetcher', 'calendar-fetcher',
     '{"calendar": "work", "description": "Work calendar sync"}'),
    
    -- Other scheduled consumers
    ('hackernews-fetcher-default', 'HackerNews Fetcher', 'service_fetcher', 'hackernews-fetcher',
     '{"description": "Fetches saved HackerNews items"}'),
    
    -- Generic scheduled consumer
    ('scheduled-consumer-default', 'Default Scheduled Consumer', 'service_consumer', 'scheduled-consumer',
     '{"description": "Generic scheduled task consumer"}')
ON CONFLICT (device_id) DO NOTHING;

-- Add comment
COMMENT ON TABLE devices IS 'Registry of all devices and services that send data to Loom, including physical devices and scheduled services';
COMMENT ON COLUMN devices.device_id IS 'Unique identifier for the device/service (matches device_id in data tables)';
COMMENT ON COLUMN devices.name IS 'Human-readable name for the device';
COMMENT ON COLUMN devices.device_type IS 'Type of device or service';
COMMENT ON COLUMN devices.service_name IS 'For service types: name of the service (e.g., email-fetcher)';
COMMENT ON COLUMN devices.service_config IS 'For services: configuration data specific to the service';

-- Create function to auto-register devices
CREATE OR REPLACE FUNCTION auto_register_device(
    p_device_id TEXT,
    p_device_type TEXT DEFAULT 'other',
    p_metadata JSONB DEFAULT '{}'
) RETURNS void AS $$
BEGIN
    INSERT INTO devices (device_id, name, device_type, metadata, last_seen_at)
    VALUES (
        p_device_id,
        CASE 
            WHEN p_device_id LIKE 'email-fetcher-%' THEN 'Email Fetcher (' || p_device_id || ')'
            WHEN p_device_id LIKE 'x-likes-%' THEN 'X Likes Fetcher (' || p_device_id || ')'
            WHEN p_device_id LIKE 'calendar-%' THEN 'Calendar Sync (' || p_device_id || ')'
            ELSE 'Unknown Device (' || p_device_id || ')'
        END,
        p_device_type,
        p_metadata,
        NOW()
    )
    ON CONFLICT (device_id) DO UPDATE
    SET last_seen_at = NOW(),
        metadata = devices.metadata || p_metadata;
END;
$$ LANGUAGE plpgsql;

-- Create view for device activity summary
CREATE OR REPLACE VIEW device_activity_summary AS
WITH recent_activity AS (
    -- Get activity from various raw data tables
    SELECT device_id, MAX(timestamp) as last_activity 
    FROM device_audio_raw 
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY device_id
    
    UNION ALL
    
    SELECT device_id, MAX(timestamp) as last_activity 
    FROM device_sensor_gps_raw 
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY device_id
    
    UNION ALL
    
    SELECT device_id, MAX(timestamp) as last_activity 
    FROM digital_clipboard_raw 
    WHERE timestamp > NOW() - INTERVAL '7 days'
    GROUP BY device_id
    
    -- Add more tables as needed
)
SELECT 
    d.device_id,
    d.name,
    d.device_type,
    d.service_name,
    d.is_active,
    MAX(ra.last_activity) as last_data_received,
    d.last_seen_at,
    CASE 
        WHEN MAX(ra.last_activity) > NOW() - INTERVAL '1 hour' THEN 'active'
        WHEN MAX(ra.last_activity) > NOW() - INTERVAL '24 hours' THEN 'idle'
        WHEN MAX(ra.last_activity) > NOW() - INTERVAL '7 days' THEN 'inactive'
        ELSE 'offline'
    END as status
FROM devices d
LEFT JOIN recent_activity ra ON d.device_id = ra.device_id
GROUP BY d.device_id, d.name, d.device_type, d.service_name, d.is_active, d.last_seen_at;