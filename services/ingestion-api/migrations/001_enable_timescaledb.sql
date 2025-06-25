-- Migration 001: Enable TimescaleDB Extension
-- Description: Enables TimescaleDB extension for time-series data optimization

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb';

-- Enable optimizations
SET timescaledb.telemetry_level = 'off';
