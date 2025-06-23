-- Migration 008: Create Device Input Tables
-- Description: Creates tables for device input data (keyboard, mouse, touch, etc.)

-- Device Keyboard Input Table
CREATE TABLE IF NOT EXISTS device_input_keyboard_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    key_code TEXT NOT NULL,
    key_name TEXT,
    action TEXT NOT NULL CHECK (action IN ('press', 'release', 'hold')),
    modifiers TEXT[],
    application_context TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Mouse Input Table
CREATE TABLE IF NOT EXISTS device_input_mouse_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    x_position INT NOT NULL,
    y_position INT NOT NULL,
    button TEXT,
    action TEXT NOT NULL CHECK (action IN ('move', 'click', 'double_click', 'drag', 'scroll')),
    scroll_delta_x INT,
    scroll_delta_y INT,
    application_context TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp)
);

-- Device Touch Input Table
CREATE TABLE IF NOT EXISTS device_input_touch_raw (
    id BIGSERIAL,
    device_id TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    touch_id INT NOT NULL,
    x_position DOUBLE PRECISION NOT NULL,
    y_position DOUBLE PRECISION NOT NULL,
    pressure DOUBLE PRECISION,
    action TEXT NOT NULL CHECK (action IN ('touch_down', 'touch_move', 'touch_up', 'touch_cancel')),
    gesture_type TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (device_id, timestamp, touch_id)
);

-- Convert tables to hypertables
SELECT create_hypertable('device_input_keyboard_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_input_mouse_raw', 'timestamp', if_not_exists => TRUE);
SELECT create_hypertable('device_input_touch_raw', 'timestamp', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_keyboard_device_time ON device_input_keyboard_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mouse_device_time ON device_input_mouse_raw (device_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_touch_device_time ON device_input_touch_raw (device_id, timestamp DESC);