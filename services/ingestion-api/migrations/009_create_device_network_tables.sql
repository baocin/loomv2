-- Migration 009: Create Device Network Tables
-- Description: Creates tables for device network data (WiFi, Bluetooth, etc.)

-- Device WiFi Network Table
CREATE TABLE IF NOT EXISTS device_network_wifi_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    ssid TEXT NOT NULL,
    bssid TEXT,
    signal_strength INT,
    frequency INT,
    channel INT,
    security_type TEXT,
    is_connected BOOLEAN NOT NULL,
    ip_address INET,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, ssid)
);

-- Device Bluetooth Table
CREATE TABLE IF NOT EXISTS device_network_bluetooth_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    bluetooth_mac TEXT NOT NULL,
    device_name TEXT,
    device_type TEXT,
    signal_strength INT,
    is_connected BOOLEAN NOT NULL,
    is_paired BOOLEAN NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, bluetooth_mac)
);

-- Device Network Stats Table
CREATE TABLE IF NOT EXISTS device_network_stats_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    interface_name TEXT NOT NULL,
    bytes_sent BIGINT NOT NULL,
    bytes_received BIGINT NOT NULL,
    packets_sent BIGINT NOT NULL,
    packets_received BIGINT NOT NULL,
    errors_in INT,
    errors_out INT,
    drops_in INT,
    drops_out INT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, interface_name)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_network_wifi_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_network_bluetooth_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_network_stats_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_wifi_device_time ON device_network_wifi_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bluetooth_device_time ON device_network_bluetooth_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_network_stats_device_time ON device_network_stats_raw (device_id, timestamp DESC);
