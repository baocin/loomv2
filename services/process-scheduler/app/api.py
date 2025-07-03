#!/usr/bin/env python3
"""
Process Scheduler Management API

REST API for managing scheduled processes, viewing execution history,
and triggering manual executions.
"""

from datetime import datetime, timezone
from typing import List, Optional

import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .scheduler import ScheduledProcess, ProcessExecution

logger = structlog.get_logger(__name__)


class ProcessCreate(BaseModel):
    """Model for creating a new scheduled process."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    cron_expression: str = Field(..., description="Cron expression (e.g., '0 */5 * * *')")
    timezone: str = Field(default="UTC")
    process_type: str = Field(..., description="Process type: kafka_consumer, data_pipeline, scraper, cleanup, retry_processor")
    target_service: str = Field(..., max_length=100)
    configuration: dict = Field(default_factory=dict)
    max_execution_time_seconds: int = Field(default=3600, gt=0)
    max_concurrent_executions: int = Field(default=1, gt=0)
    retry_on_failure: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0)
    retry_delay_seconds: int = Field(default=300, ge=0)
    enabled: bool = Field(default=True)
    priority: int = Field(default=5, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)


class ProcessUpdate(BaseModel):
    """Model for updating a scheduled process."""
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    configuration: Optional[dict] = None
    max_execution_time_seconds: Optional[int] = Field(None, gt=0)
    max_concurrent_executions: Optional[int] = Field(None, gt=0)
    retry_on_failure: Optional[bool] = None
    max_retries: Optional[int] = Field(None, ge=0)
    retry_delay_seconds: Optional[int] = Field(None, ge=0)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None


class ExecutionSummary(BaseModel):
    """Summary model for process execution."""
    id: int
    process_id: int
    process_name: str
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    execution_status: str
    duration_seconds: Optional[float]
    exit_code: Optional[int]
    error_message: Optional[str]
    retry_attempt: int
    triggered_by: str


class ProcessStatus(BaseModel):
    """Model for process status summary."""
    id: int
    name: str
    enabled: bool
    last_execution_status: Optional[str]
    last_execution_time: Optional[datetime]
    next_scheduled_time: Optional[datetime]
    running_executions: int


# Database dependency
async def get_db_connection():
    """Get database connection dependency."""
    database_url = "postgresql://loom:loom@localhost:5432/loom"  # From config
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


# FastAPI app
app = FastAPI(
    title="Loom Process Scheduler API",
    description="API for managing scheduled processes and viewing execution history",
    version="0.1.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@app.get("/processes", response_model=List[ScheduledProcess])
async def list_processes(
    enabled: Optional[bool] = None,
    process_type: Optional[str] = None,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """List all scheduled processes with optional filtering."""
    
    query = "SELECT * FROM scheduled_processes WHERE 1=1"
    params = []
    
    if enabled is not None:
        query += " AND enabled = $" + str(len(params) + 1)
        params.append(enabled)
        
    if process_type is not None:
        query += " AND process_type = $" + str(len(params) + 1)
        params.append(process_type)
    
    query += " ORDER BY priority ASC, name ASC"
    
    rows = await conn.fetch(query, *params)
    return [ScheduledProcess(**dict(row)) for row in rows]


@app.get("/processes/{process_id}", response_model=ScheduledProcess)
async def get_process(
    process_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get a specific scheduled process by ID."""
    
    row = await conn.fetchrow(
        "SELECT * FROM scheduled_processes WHERE id = $1",
        process_id
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    return ScheduledProcess(**dict(row))


@app.post("/processes", response_model=ScheduledProcess, status_code=status.HTTP_201_CREATED)
async def create_process(
    process: ProcessCreate,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Create a new scheduled process."""
    
    # Validate cron expression
    try:
        from croniter import croniter
        croniter(process.cron_expression)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {e}"
        )
    
    # Check if name already exists
    existing = await conn.fetchval(
        "SELECT id FROM scheduled_processes WHERE name = $1",
        process.name
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Process name already exists"
        )
    
    # Insert new process
    row = await conn.fetchrow("""
        INSERT INTO scheduled_processes (
            name, description, cron_expression, timezone, process_type,
            target_service, configuration, max_execution_time_seconds,
            max_concurrent_executions, retry_on_failure, max_retries,
            retry_delay_seconds, enabled, priority, tags
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        RETURNING *
    """,
        process.name, process.description, process.cron_expression,
        process.timezone, process.process_type, process.target_service,
        process.configuration, process.max_execution_time_seconds,
        process.max_concurrent_executions, process.retry_on_failure,
        process.max_retries, process.retry_delay_seconds,
        process.enabled, process.priority, process.tags
    )
    
    logger.info("Created scheduled process", process_name=process.name, process_id=row["id"])
    
    return ScheduledProcess(**dict(row))


@app.put("/processes/{process_id}", response_model=ScheduledProcess)
async def update_process(
    process_id: int,
    updates: ProcessUpdate,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Update a scheduled process."""
    
    # Check if process exists
    existing = await conn.fetchrow(
        "SELECT * FROM scheduled_processes WHERE id = $1",
        process_id
    )
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    # Validate cron expression if provided
    if updates.cron_expression:
        try:
            from croniter import croniter
            croniter(updates.cron_expression)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {e}"
            )
    
    # Build update query
    update_fields = []
    params = []
    
    for field, value in updates.model_dump(exclude_none=True).items():
        if value is not None:
            update_fields.append(f"{field} = ${len(params) + 1}")
            params.append(value)
    
    if not update_fields:
        return ScheduledProcess(**dict(existing))
    
    update_fields.append(f"updated_at = ${len(params) + 1}")
    params.append(datetime.now(timezone.utc))
    params.append(process_id)
    
    query = f"""
        UPDATE scheduled_processes 
        SET {', '.join(update_fields)}
        WHERE id = ${len(params)}
        RETURNING *
    """
    
    row = await conn.fetchrow(query, *params)
    
    logger.info("Updated scheduled process", process_id=process_id, updated_fields=list(updates.model_dump(exclude_none=True).keys()))
    
    return ScheduledProcess(**dict(row))


@app.delete("/processes/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_process(
    process_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Delete a scheduled process."""
    
    result = await conn.execute(
        "DELETE FROM scheduled_processes WHERE id = $1",
        process_id
    )
    
    if result == "DELETE 0":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    logger.info("Deleted scheduled process", process_id=process_id)


@app.post("/processes/{process_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def trigger_manual_execution(
    process_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Trigger a manual execution of a process."""
    
    # Check if process exists and is enabled
    process = await conn.fetchrow(
        "SELECT * FROM scheduled_processes WHERE id = $1",
        process_id
    )
    
    if not process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Process not found"
        )
    
    if not process["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Process is disabled"
        )
    
    # Check concurrent execution limit
    running_count = await conn.fetchval("""
        SELECT COUNT(*)
        FROM process_executions 
        WHERE process_id = $1 AND execution_status = 'running'
    """, process_id)
    
    if running_count >= process["max_concurrent_executions"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Process is already at maximum concurrent executions"
        )
    
    # Create execution record
    execution_id = await conn.fetchval("""
        INSERT INTO process_executions (
            process_id, scheduled_at, execution_status, 
            configuration_snapshot, triggered_by
        ) VALUES ($1, $2, $3, $4, $5)
        RETURNING id
    """, 
        process_id,
        datetime.now(timezone.utc),
        "scheduled",
        process["configuration"],
        "manual"
    )
    
    logger.info("Triggered manual execution", process_id=process_id, execution_id=execution_id)
    
    return {"execution_id": execution_id, "status": "scheduled"}


@app.get("/processes/{process_id}/executions", response_model=List[ExecutionSummary])
async def get_process_executions(
    process_id: int,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get execution history for a process."""
    
    query = """
        SELECT pe.*, sp.name as process_name
        FROM process_executions pe
        JOIN scheduled_processes sp ON pe.process_id = sp.id
        WHERE pe.process_id = $1
    """
    params = [process_id]
    
    if status_filter:
        query += " AND pe.execution_status = $" + str(len(params) + 1)
        params.append(status_filter)
    
    query += " ORDER BY pe.scheduled_at DESC LIMIT $" + str(len(params) + 1)
    params.append(limit)
    
    query += " OFFSET $" + str(len(params) + 1)
    params.append(offset)
    
    rows = await conn.fetch(query, *params)
    
    return [
        ExecutionSummary(
            id=row["id"],
            process_id=row["process_id"],
            process_name=row["process_name"],
            scheduled_at=row["scheduled_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            execution_status=row["execution_status"],
            duration_seconds=row["duration_seconds"],
            exit_code=row["exit_code"],
            error_message=row["error_message"],
            retry_attempt=row["retry_attempt"],
            triggered_by=row["triggered_by"]
        )
        for row in rows
    ]


@app.get("/executions/{execution_id}", response_model=ProcessExecution)
async def get_execution_details(
    execution_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get detailed information about a specific execution."""
    
    row = await conn.fetchrow(
        "SELECT * FROM process_executions WHERE id = $1",
        execution_id
    )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return ProcessExecution(**dict(row))


@app.get("/status", response_model=List[ProcessStatus])
async def get_processes_status(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """Get current status overview of all processes."""
    
    rows = await conn.fetch("""
        SELECT 
            sp.id,
            sp.name,
            sp.enabled,
            latest.execution_status as last_execution_status,
            latest.completed_at as last_execution_time,
            NULL::timestamptz as next_scheduled_time,
            COALESCE(running.count, 0) as running_executions
        FROM scheduled_processes sp
        LEFT JOIN LATERAL (
            SELECT execution_status, completed_at
            FROM process_executions pe
            WHERE pe.process_id = sp.id
            ORDER BY pe.scheduled_at DESC
            LIMIT 1
        ) latest ON true
        LEFT JOIN LATERAL (
            SELECT COUNT(*) as count
            FROM process_executions pe2
            WHERE pe2.process_id = sp.id 
            AND pe2.execution_status = 'running'
        ) running ON true
        ORDER BY sp.priority ASC, sp.name ASC
    """)
    
    return [
        ProcessStatus(
            id=row["id"],
            name=row["name"],
            enabled=row["enabled"],
            last_execution_status=row["last_execution_status"],
            last_execution_time=row["last_execution_time"],
            next_scheduled_time=row["next_scheduled_time"],
            running_executions=row["running_executions"]
        )
        for row in rows
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)