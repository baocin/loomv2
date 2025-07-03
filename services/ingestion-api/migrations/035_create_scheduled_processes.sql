-- Migration: Create scheduled processes management tables
-- Purpose: Manage scheduled processes with execution tracking
-- Dependencies: TimescaleDB extension

-- Table for scheduled process definitions
CREATE TABLE scheduled_processes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    
    -- Schedule definition
    cron_expression VARCHAR(100) NOT NULL, -- Standard cron format: "0 */5 * * *"
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Process configuration
    process_type VARCHAR(50) NOT NULL, -- 'kafka_consumer', 'data_pipeline', 'cleanup', 'scraper'
    target_service VARCHAR(100) NOT NULL, -- Service/consumer to execute
    configuration JSONB DEFAULT '{}', -- Process-specific configuration
    
    -- Execution settings
    max_execution_time_seconds INTEGER DEFAULT 3600, -- 1 hour default timeout
    max_concurrent_executions INTEGER DEFAULT 1, -- Prevent overlapping executions
    retry_on_failure BOOLEAN DEFAULT true,
    max_retries INTEGER DEFAULT 3,
    retry_delay_seconds INTEGER DEFAULT 300, -- 5 minutes
    
    -- Status and metadata
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 5, -- 1 = highest, 10 = lowest
    tags TEXT[] DEFAULT '{}', -- For grouping and filtering
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Create indexes for efficient querying
CREATE INDEX idx_scheduled_processes_enabled ON scheduled_processes (enabled);
CREATE INDEX idx_scheduled_processes_process_type ON scheduled_processes (process_type);
CREATE INDEX idx_scheduled_processes_priority ON scheduled_processes (priority);
CREATE INDEX idx_scheduled_processes_tags ON scheduled_processes USING GIN (tags);

-- Table for process execution tracking (hypertable for time-series data)
CREATE TABLE process_executions (
    id BIGSERIAL,
    process_id INTEGER NOT NULL REFERENCES scheduled_processes(id) ON DELETE CASCADE,
    
    -- Execution timing
    scheduled_at TIMESTAMPTZ NOT NULL, -- When it was supposed to run
    started_at TIMESTAMPTZ, -- When execution actually began
    completed_at TIMESTAMPTZ, -- When execution finished
    
    -- Execution details
    execution_status VARCHAR(20) NOT NULL DEFAULT 'scheduled', 
    -- Values: 'scheduled', 'running', 'completed', 'failed', 'timeout', 'cancelled'
    
    exit_code INTEGER, -- Process exit code
    error_message TEXT, -- Error details if failed
    
    -- Process information
    executor_host VARCHAR(255), -- Which host/pod executed the process
    executor_pid INTEGER, -- Process ID on the executor
    
    -- Execution metrics
    duration_seconds REAL, -- Calculated: completed_at - started_at
    memory_usage_mb INTEGER, -- Peak memory usage
    cpu_usage_percent REAL, -- Average CPU usage
    
    -- Output and logs
    stdout_log TEXT, -- Captured stdout (truncated)
    stderr_log TEXT, -- Captured stderr (truncated)
    log_file_path VARCHAR(500), -- Path to full log file
    
    -- Metadata
    configuration_snapshot JSONB, -- Config used for this execution
    retry_attempt INTEGER DEFAULT 0, -- Which retry attempt (0 = first try)
    triggered_by VARCHAR(100), -- 'scheduler', 'manual', 'api', 'dependency'
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for efficient time-series operations
SELECT create_hypertable('process_executions', 'scheduled_at', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for process execution queries
CREATE INDEX idx_process_executions_process_id ON process_executions (process_id);
CREATE INDEX idx_process_executions_status ON process_executions (execution_status);
CREATE INDEX idx_process_executions_scheduled_at ON process_executions (scheduled_at DESC);
CREATE INDEX idx_process_executions_started_at ON process_executions (started_at DESC) WHERE started_at IS NOT NULL;
CREATE INDEX idx_process_executions_completed_at ON process_executions (completed_at DESC) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_process_executions_executor_host ON process_executions (executor_host);

-- Table for process dependencies (optional: processes that depend on others)
CREATE TABLE process_dependencies (
    id SERIAL PRIMARY KEY,
    dependent_process_id INTEGER NOT NULL REFERENCES scheduled_processes(id) ON DELETE CASCADE,
    dependency_process_id INTEGER NOT NULL REFERENCES scheduled_processes(id) ON DELETE CASCADE,
    
    -- Dependency configuration
    dependency_type VARCHAR(20) DEFAULT 'success', -- 'success', 'completion', 'failure'
    max_wait_time_seconds INTEGER DEFAULT 3600, -- How long to wait for dependency
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(dependent_process_id, dependency_process_id),
    CHECK (dependent_process_id != dependency_process_id) -- Prevent self-dependency
);

-- Create indexes for dependency queries
CREATE INDEX idx_process_dependencies_dependent ON process_dependencies (dependent_process_id);
CREATE INDEX idx_process_dependencies_dependency ON process_dependencies (dependency_process_id);

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_scheduled_processes_updated_at 
    BEFORE UPDATE ON scheduled_processes 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate execution duration
CREATE OR REPLACE FUNCTION calculate_execution_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.started_at IS NOT NULL AND NEW.completed_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically calculate duration
CREATE TRIGGER calculate_process_execution_duration 
    BEFORE INSERT OR UPDATE ON process_executions 
    FOR EACH ROW 
    EXECUTE FUNCTION calculate_execution_duration();

-- View for current process status (latest execution per process)
CREATE VIEW process_status_current AS
SELECT 
    sp.id,
    sp.name,
    sp.description,
    sp.process_type,
    sp.cron_expression,
    sp.enabled,
    sp.priority,
    
    -- Latest execution info
    pe.scheduled_at as last_scheduled_at,
    pe.started_at as last_started_at,
    pe.completed_at as last_completed_at,
    pe.execution_status as last_execution_status,
    pe.duration_seconds as last_duration_seconds,
    pe.error_message as last_error_message,
    pe.retry_attempt as last_retry_attempt,
    
    -- Next scheduled time (calculated based on cron and last execution)
    -- This would need to be calculated by the scheduler service
    NULL::TIMESTAMPTZ as next_scheduled_at
    
FROM scheduled_processes sp
LEFT JOIN LATERAL (
    SELECT * 
    FROM process_executions pe2 
    WHERE pe2.process_id = sp.id 
    ORDER BY pe2.scheduled_at DESC 
    LIMIT 1
) pe ON true;

-- Insert some example scheduled processes
INSERT INTO scheduled_processes (
    name, description, cron_expression, process_type, target_service, configuration, priority
) VALUES 
    (
        'twitter_scraper_daily',
        'Daily Twitter scraping for liked posts',
        '0 2 * * *', -- Run at 2 AM daily
        'scraper',
        'twitter-scraper',
        '{"max_posts": 100, "include_retweets": false}',
        3
    ),
    (
        'email_fetcher_hourly',
        'Hourly email fetching from IMAP accounts',
        '0 * * * *', -- Run every hour
        'data_pipeline',
        'email-fetcher',
        '{"batch_size": 50, "mark_as_read": false}',
        2
    ),
    (
        'audio_processing_batch',
        'Process accumulated audio chunks for transcription',
        '*/15 * * * *', -- Every 15 minutes
        'kafka_consumer',
        'audio-transcription-consumer',
        '{"batch_size": 100, "min_duration_seconds": 5}',
        1
    ),
    (
        'cleanup_old_logs',
        'Clean up log files older than 7 days',
        '0 3 * * 0', -- Weekly at 3 AM on Sunday
        'cleanup',
        'log-cleanup-service',
        '{"retention_days": 7, "log_paths": ["/var/log/loom"]}',
        5
    ),
    (
        'geocoding_batch_process',
        'Batch process GPS coordinates for geocoding',
        '*/30 * * * *', -- Every 30 minutes
        'kafka_consumer',
        'gps-geocoding-consumer',
        '{"batch_size": 500, "rate_limit_per_second": 10}',
        2
    ),
    (
        'health_metrics_aggregation',
        'Aggregate health metrics into daily summaries',
        '0 1 * * *', -- Daily at 1 AM
        'data_pipeline',
        'health-aggregator',
        '{"aggregation_window": "24h", "metrics": ["steps", "heartrate", "sleep"]}',
        3
    ),
    (
        'twitter_extraction_retry',
        'Retry failed Twitter extractions with no extracted text',
        '0 */4 * * *', -- Every 4 hours
        'retry_processor',
        'twitter-extraction-retry',
        '{"batch_size": 100, "max_retry_attempts": 3, "min_age_hours": 2, "max_age_days": 7, "retry_topic": "task.url.ingest"}',
        2
    );

-- Grant permissions (adjust as needed for your user setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON scheduled_processes TO loom_scheduler;
-- GRANT SELECT, INSERT, UPDATE ON process_executions TO loom_scheduler;
-- GRANT SELECT ON process_dependencies TO loom_scheduler;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO loom_scheduler;

COMMENT ON TABLE scheduled_processes IS 'Definitions of scheduled processes with cron expressions and configuration';
COMMENT ON TABLE process_executions IS 'Time-series tracking of process execution history and status';
COMMENT ON TABLE process_dependencies IS 'Optional dependencies between scheduled processes';
COMMENT ON VIEW process_status_current IS 'Current status view showing latest execution for each process';