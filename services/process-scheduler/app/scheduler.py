#!/usr/bin/env python3
"""
Loom Process Scheduler Service

Manages scheduled processes defined in TimescaleDB, triggering them based on
cron expressions and tracking execution status.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncpg
import structlog
from croniter import croniter
from pydantic import BaseModel

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class ScheduledProcess(BaseModel):
    """Model for scheduled process definition."""
    id: int
    name: str
    description: Optional[str]
    cron_expression: str
    timezone: str
    process_type: str
    target_service: str
    configuration: Dict[str, Any]
    max_execution_time_seconds: int
    max_concurrent_executions: int
    retry_on_failure: bool
    max_retries: int
    retry_delay_seconds: int
    enabled: bool
    priority: int
    tags: List[str]


class ProcessExecution(BaseModel):
    """Model for process execution tracking."""
    id: Optional[int] = None
    process_id: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_status: str = "scheduled"
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    executor_host: Optional[str] = None
    executor_pid: Optional[int] = None
    configuration_snapshot: Dict[str, Any]
    retry_attempt: int = 0
    triggered_by: str = "scheduler"


class ProcessScheduler:
    """Main scheduler service for managing scheduled processes."""
    
    def __init__(self, database_url: str, check_interval: int = 60):
        self.database_url = database_url
        self.check_interval = check_interval
        self.running = False
        self.db_pool: Optional[asyncpg.Pool] = None
        self.running_processes: Dict[int, asyncio.Task] = {}
        self.hostname = os.uname().nodename
        
    async def start(self):
        """Start the scheduler service."""
        logger.info("Starting process scheduler", hostname=self.hostname)
        
        # Create database connection pool
        self.db_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        self.running = True
        
        # Start main scheduler loop
        await self._scheduler_loop()
    
    async def stop(self):
        """Stop the scheduler service."""
        logger.info("Stopping process scheduler")
        self.running = False
        
        # Cancel all running processes
        for task in self.running_processes.values():
            if not task.done():
                task.cancel()
                
        # Wait for processes to complete
        if self.running_processes:
            await asyncio.gather(*self.running_processes.values(), return_exceptions=True)
            
        # Close database pool
        if self.db_pool:
            await self.db_pool.close()
    
    async def _scheduler_loop(self):
        """Main scheduler loop that checks for processes to run."""
        while self.running:
            try:
                await self._check_and_schedule_processes()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error("Error in scheduler loop", error=str(e), exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    async def _check_and_schedule_processes(self):
        """Check for processes that need to be scheduled and run them."""
        if not self.db_pool:
            return
            
        # Get enabled processes
        async with self.db_pool.acquire() as conn:
            processes = await self._get_enabled_processes(conn)
            
        current_time = datetime.now(timezone.utc)
        
        for process in processes:
            try:
                if await self._should_run_process(process, current_time):
                    await self._schedule_process(process, current_time)
            except Exception as e:
                logger.error(
                    "Error checking process",
                    process_name=process.name,
                    error=str(e),
                    exc_info=True
                )
    
    async def _get_enabled_processes(self, conn: asyncpg.Connection) -> List[ScheduledProcess]:
        """Get all enabled scheduled processes."""
        query = """
        SELECT id, name, description, cron_expression, timezone, process_type,
               target_service, configuration, max_execution_time_seconds,
               max_concurrent_executions, retry_on_failure, max_retries,
               retry_delay_seconds, enabled, priority, tags
        FROM scheduled_processes 
        WHERE enabled = true
        ORDER BY priority ASC, name ASC
        """
        
        rows = await conn.fetch(query)
        return [ScheduledProcess(**dict(row)) for row in rows]
    
    async def _should_run_process(self, process: ScheduledProcess, current_time: datetime) -> bool:
        """Determine if a process should be run now."""
        if not self.db_pool:
            return False
            
        # Check if process is already running
        running_count = await self._get_running_process_count(process.id)
        if running_count >= process.max_concurrent_executions:
            logger.debug(
                "Process already at max concurrent executions",
                process_name=process.name,
                running_count=running_count,
                max_concurrent=process.max_concurrent_executions
            )
            return False
        
        # Get last execution time
        async with self.db_pool.acquire() as conn:
            last_execution = await conn.fetchrow("""
                SELECT scheduled_at, execution_status
                FROM process_executions 
                WHERE process_id = $1 
                ORDER BY scheduled_at DESC 
                LIMIT 1
            """, process.id)
        
        # Calculate next run time based on cron expression
        cron = croniter(process.cron_expression, current_time)
        
        if last_execution is None:
            # Never run before, schedule immediately
            return True
            
        last_scheduled = last_execution['scheduled_at']
        next_run_time = cron.get_prev(datetime)
        
        # Check if we've passed the next scheduled time
        return current_time >= next_run_time and last_scheduled < next_run_time
    
    async def _get_running_process_count(self, process_id: int) -> int:
        """Get count of currently running executions for a process."""
        if not self.db_pool:
            return 0
            
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT COUNT(*)
                FROM process_executions 
                WHERE process_id = $1 
                AND execution_status = 'running'
            """, process_id)
            
        return result or 0
    
    async def _schedule_process(self, process: ScheduledProcess, scheduled_time: datetime):
        """Schedule a process execution."""
        logger.info(
            "Scheduling process execution",
            process_name=process.name,
            process_type=process.process_type,
            target_service=process.target_service
        )
        
        # Create execution record
        execution = ProcessExecution(
            process_id=process.id,
            scheduled_at=scheduled_time,
            configuration_snapshot=process.configuration,
            executor_host=self.hostname
        )
        
        # Insert execution record
        if not self.db_pool:
            return
            
        async with self.db_pool.acquire() as conn:
            execution_id = await conn.fetchval("""
                INSERT INTO process_executions (
                    process_id, scheduled_at, execution_status, executor_host,
                    configuration_snapshot, triggered_by
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, 
                execution.process_id,
                execution.scheduled_at,
                execution.execution_status,
                execution.executor_host,
                json.dumps(execution.configuration_snapshot),
                execution.triggered_by
            )
            
        execution.id = execution_id
        
        # Start process execution
        task = asyncio.create_task(self._execute_process(process, execution))
        self.running_processes[execution_id] = task
        
        # Clean up completed tasks
        task.add_done_callback(lambda t: self.running_processes.pop(execution_id, None))
    
    async def _execute_process(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a scheduled process."""
        logger.info(
            "Starting process execution",
            process_name=process.name,
            execution_id=execution.id,
            target_service=process.target_service
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Update status to running
            await self._update_execution_status(
                execution.id,
                "running",
                started_at=start_time,
                executor_pid=os.getpid()
            )
            
            # Execute based on process type
            if process.process_type == "kafka_consumer":
                await self._execute_kafka_consumer(process, execution)
            elif process.process_type == "data_pipeline":
                await self._execute_data_pipeline(process, execution)
            elif process.process_type == "scraper":
                await self._execute_scraper(process, execution)
            elif process.process_type == "cleanup":
                await self._execute_cleanup(process, execution)
            elif process.process_type == "retry_processor":
                await self._execute_retry_processor(process, execution)
            else:
                raise ValueError(f"Unknown process type: {process.process_type}")
            
            # Mark as completed
            completed_time = datetime.now(timezone.utc)
            await self._update_execution_status(
                execution.id,
                "completed",
                completed_at=completed_time,
                exit_code=0
            )
            
            logger.info(
                "Process execution completed successfully",
                process_name=process.name,
                execution_id=execution.id,
                duration_seconds=(completed_time - start_time).total_seconds()
            )
            
        except asyncio.TimeoutError:
            logger.error(
                "Process execution timed out",
                process_name=process.name,
                execution_id=execution.id,
                timeout_seconds=process.max_execution_time_seconds
            )
            
            await self._update_execution_status(
                execution.id,
                "timeout",
                completed_at=datetime.now(timezone.utc),
                error_message="Process execution timed out"
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Process execution failed",
                process_name=process.name,
                execution_id=execution.id,
                error=error_msg,
                exc_info=True
            )
            
            await self._update_execution_status(
                execution.id,
                "failed",
                completed_at=datetime.now(timezone.utc),
                error_message=error_msg,
                exit_code=1
            )
            
            # Handle retries
            if process.retry_on_failure and execution.retry_attempt < process.max_retries:
                await self._schedule_retry(process, execution)
    
    async def _execute_kafka_consumer(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a Kafka consumer process."""
        config = execution.configuration_snapshot
        
        # Build command based on target service
        if process.target_service == "audio-transcription-consumer":
            cmd = [
                "python", "-m", "services.audio-transcription-consumer.app.consumer",
                "--batch-size", str(config.get("batch_size", 100)),
                "--min-duration", str(config.get("min_duration_seconds", 5))
            ]
        elif process.target_service == "gps-geocoding-consumer":
            cmd = [
                "python", "-m", "services.gps-geocoding-consumer.app.consumer",
                "--batch-size", str(config.get("batch_size", 500)),
                "--rate-limit", str(config.get("rate_limit_per_second", 10))
            ]
        else:
            raise ValueError(f"Unknown Kafka consumer service: {process.target_service}")
        
        await self._run_subprocess(cmd, process.max_execution_time_seconds)
    
    async def _execute_data_pipeline(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a data pipeline process."""
        config = execution.configuration_snapshot
        
        if process.target_service == "email-fetcher":
            cmd = [
                "python", "-m", "services.email-fetcher.app.main",
                "--batch-size", str(config.get("batch_size", 50))
            ]
        elif process.target_service == "health-aggregator":
            cmd = [
                "python", "-m", "services.health-aggregator.app.main",
                "--window", config.get("aggregation_window", "24h")
            ]
        else:
            raise ValueError(f"Unknown data pipeline service: {process.target_service}")
        
        await self._run_subprocess(cmd, process.max_execution_time_seconds)
    
    async def _execute_scraper(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a scraper process."""
        config = execution.configuration_snapshot
        
        if process.target_service == "twitter-scraper":
            cmd = [
                "python", "-m", "services.twitter-scraper.app.main",
                "--max-posts", str(config.get("max_posts", 100))
            ]
            if not config.get("include_retweets", False):
                cmd.append("--no-retweets")
        else:
            raise ValueError(f"Unknown scraper service: {process.target_service}")
        
        await self._run_subprocess(cmd, process.max_execution_time_seconds)
    
    async def _execute_cleanup(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a cleanup process."""
        config = execution.configuration_snapshot
        
        if process.target_service == "log-cleanup-service":
            retention_days = config.get("retention_days", 7)
            log_paths = config.get("log_paths", ["/var/log/loom"])
            
            cmd = ["find"] + log_paths + [
                "-name", "*.log",
                "-mtime", f"+{retention_days}",
                "-delete"
            ]
        else:
            raise ValueError(f"Unknown cleanup service: {process.target_service}")
        
        await self._run_subprocess(cmd, process.max_execution_time_seconds)
    
    async def _execute_retry_processor(self, process: ScheduledProcess, execution: ProcessExecution):
        """Execute a retry processor."""
        config = execution.configuration_snapshot
        
        if process.target_service == "twitter-extraction-retry":
            from .processors.twitter_retry import TwitterExtractionRetryProcessor
            
            processor = TwitterExtractionRetryProcessor(config)
            results = await processor.process()
            
            # Log results for monitoring
            logger.info(
                "Retry processor completed",
                service=process.target_service,
                results=results
            )
            
            # If there were significant errors, we might want to raise an exception
            if results.get("errors", 0) > results.get("processed", 0) * 0.5:
                raise RuntimeError(f"Too many errors in retry processing: {results}")
        else:
            raise ValueError(f"Unknown retry processor service: {process.target_service}")
    
    async def _run_subprocess(self, cmd: List[str], timeout_seconds: int):
        """Run a subprocess with timeout."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_seconds
            )
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode,
                    cmd,
                    output=stdout,
                    stderr=stderr
                )
                
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            raise asyncio.TimeoutError("Process execution timed out")
    
    async def _update_execution_status(
        self,
        execution_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
        executor_pid: Optional[int] = None
    ):
        """Update execution status in database."""
        if not self.db_pool:
            return
            
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE process_executions 
                SET execution_status = $1,
                    started_at = COALESCE($2, started_at),
                    completed_at = COALESCE($3, completed_at),
                    exit_code = COALESCE($4, exit_code),
                    error_message = COALESCE($5, error_message),
                    executor_pid = COALESCE($6, executor_pid)
                WHERE id = $7
            """, status, started_at, completed_at, exit_code, error_message, executor_pid, execution_id)
    
    async def _schedule_retry(self, process: ScheduledProcess, execution: ProcessExecution):
        """Schedule a retry for a failed process."""
        logger.info(
            "Scheduling process retry",
            process_name=process.name,
            execution_id=execution.id,
            retry_attempt=execution.retry_attempt + 1,
            delay_seconds=process.retry_delay_seconds
        )
        
        # Wait for retry delay
        await asyncio.sleep(process.retry_delay_seconds)
        
        # Create new execution record for retry
        retry_execution = ProcessExecution(
            process_id=process.id,
            scheduled_at=datetime.now(timezone.utc),
            configuration_snapshot=process.configuration,
            executor_host=self.hostname,
            retry_attempt=execution.retry_attempt + 1,
            triggered_by="retry"
        )
        
        # Start retry execution
        task = asyncio.create_task(self._execute_process(process, retry_execution))
        if retry_execution.id:
            self.running_processes[retry_execution.id] = task


async def main():
    """Main entry point for the scheduler service."""
    database_url = os.getenv("DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom")
    check_interval = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60"))
    
    scheduler = ProcessScheduler(database_url, check_interval)
    
    # Handle shutdown signals
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(scheduler.stop())
    
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    try:
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())