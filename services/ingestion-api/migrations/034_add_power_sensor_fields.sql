-- Migration 034: Add missing power sensor fields
-- Description: Add power_source, lid_closed, and thermal_state fields to device_state_power_raw table

-- Add missing power sensor fields
ALTER TABLE device_state_power_raw
ADD COLUMN IF NOT EXISTS power_source TEXT,
ADD COLUMN IF NOT EXISTS lid_closed BOOLEAN,
ADD COLUMN IF NOT EXISTS thermal_state TEXT;

-- Create index for common power state queries
CREATE INDEX IF NOT EXISTS idx_power_state_charging ON device_state_power_raw (device_id, is_charging, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_power_state_thermal ON device_state_power_raw (device_id, thermal_state, timestamp DESC) WHERE thermal_state IS NOT NULL;
