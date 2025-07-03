#!/usr/bin/env python3
"""
Utility script to manage scheduled processes.

Usage:
    python scripts/manage-scheduled-processes.py list
    python scripts/manage-scheduled-processes.py create --name "test_process" --cron "*/5 * * * *" --type kafka_consumer --service test-service
    python scripts/manage-scheduled-processes.py enable --id 1
    python scripts/manage-scheduled-processes.py disable --id 1
    python scripts/manage-scheduled-processes.py trigger --id 1
    python scripts/manage-scheduled-processes.py status
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

import asyncpg


async def connect_db() -> asyncpg.Connection:
    """Connect to the database."""
    database_url = "postgresql://loom:loom@localhost:5432/loom"
    return await asyncpg.connect(database_url)


async def list_processes(conn: asyncpg.Connection, enabled_only: bool = False):
    """List all scheduled processes."""
    query = "SELECT * FROM scheduled_processes"
    if enabled_only:
        query += " WHERE enabled = true"
    query += " ORDER BY priority ASC, name ASC"
    
    rows = await conn.fetch(query)
    
    if not rows:
        print("No scheduled processes found.")
        return
    
    print(f"{'ID':<4} {'Name':<25} {'Type':<15} {'Service':<20} {'Cron':<15} {'Enabled':<8} {'Priority'}")
    print("-" * 95)
    
    for row in rows:
        print(f"{row['id']:<4} {row['name']:<25} {row['process_type']:<15} "
              f"{row['target_service']:<20} {row['cron_expression']:<15} "
              f"{row['enabled']!s:<8} {row['priority']}")


async def create_process(
    conn: asyncpg.Connection,
    name: str,
    cron: str,
    process_type: str,
    target_service: str,
    description: Optional[str] = None,
    config: Optional[str] = None,
    priority: int = 5
):
    """Create a new scheduled process."""
    
    # Validate cron expression
    try:
        from croniter import croniter
        croniter(cron)
    except Exception as e:
        print(f"Error: Invalid cron expression: {e}")
        return False
    
    # Parse configuration JSON if provided
    configuration = {}
    if config:
        try:
            configuration = json.loads(config)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON configuration: {e}")
            return False
    
    try:
        process_id = await conn.fetchval("""
            INSERT INTO scheduled_processes (
                name, description, cron_expression, process_type, target_service,
                configuration, priority
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, name, description, cron, process_type, target_service, configuration, priority)
        
        print(f"Created scheduled process '{name}' with ID {process_id}")
        return True
        
    except asyncpg.UniqueViolationError:
        print(f"Error: Process with name '{name}' already exists")
        return False
    except Exception as e:
        print(f"Error creating process: {e}")
        return False


async def update_process_status(conn: asyncpg.Connection, process_id: int, enabled: bool):
    """Enable or disable a scheduled process."""
    
    result = await conn.execute(
        "UPDATE scheduled_processes SET enabled = $1 WHERE id = $2",
        enabled, process_id
    )
    
    if result == "UPDATE 0":
        print(f"Error: Process with ID {process_id} not found")
        return False
    
    status = "enabled" if enabled else "disabled"
    print(f"Process {process_id} {status}")
    return True


async def trigger_execution(conn: asyncpg.Connection, process_id: int):
    """Trigger a manual execution of a process."""
    
    # Check if process exists and is enabled
    process = await conn.fetchrow(
        "SELECT name, enabled, max_concurrent_executions FROM scheduled_processes WHERE id = $1",
        process_id
    )
    
    if not process:
        print(f"Error: Process with ID {process_id} not found")
        return False
    
    if not process["enabled"]:
        print(f"Error: Process '{process['name']}' is disabled")
        return False
    
    # Check concurrent execution limit
    running_count = await conn.fetchval("""
        SELECT COUNT(*)
        FROM process_executions 
        WHERE process_id = $1 AND execution_status = 'running'
    """, process_id)
    
    if running_count >= process["max_concurrent_executions"]:
        print(f"Error: Process '{process['name']}' is already at maximum concurrent executions")
        return False
    
    # Create execution record
    execution_id = await conn.fetchval("""
        INSERT INTO process_executions (
            process_id, scheduled_at, execution_status, triggered_by
        ) VALUES ($1, $2, $3, $4)
        RETURNING id
    """, process_id, datetime.now(), "scheduled", "manual")
    
    print(f"Triggered manual execution of process '{process['name']}' (execution ID: {execution_id})")
    return True


async def show_status(conn: asyncpg.Connection):
    """Show current status of all processes."""
    
    rows = await conn.fetch("""
        SELECT 
            sp.id,
            sp.name,
            sp.enabled,
            sp.process_type,
            sp.target_service,
            latest.execution_status as last_status,
            latest.completed_at as last_execution,
            latest.error_message as last_error,
            COALESCE(running.count, 0) as running_count
        FROM scheduled_processes sp
        LEFT JOIN LATERAL (
            SELECT execution_status, completed_at, error_message
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
    
    if not rows:
        print("No scheduled processes found.")
        return
    
    print("Process Status Overview:")
    print(f"{'ID':<4} {'Name':<25} {'Type':<15} {'Status':<8} {'Last Exec':<12} {'Running':<8} {'Last Error'}")
    print("-" * 110)
    
    for row in rows:
        last_exec = "Never" if not row['last_execution'] else row['last_execution'].strftime('%Y-%m-%d %H:%M')
        last_error = (row['last_error'][:30] + '...') if row['last_error'] and len(row['last_error']) > 30 else (row['last_error'] or '')
        
        print(f"{row['id']:<4} {row['name']:<25} {row['process_type']:<15} "
              f"{'✓' if row['enabled'] else '✗':<8} {last_exec:<12} "
              f"{row['running_count']:<8} {last_error}")


async def show_executions(conn: asyncpg.Connection, process_id: Optional[int] = None, limit: int = 20):
    """Show recent executions."""
    
    if process_id:
        query = """
            SELECT pe.*, sp.name as process_name
            FROM process_executions pe
            JOIN scheduled_processes sp ON pe.process_id = sp.id
            WHERE pe.process_id = $1
            ORDER BY pe.scheduled_at DESC
            LIMIT $2
        """
        rows = await conn.fetch(query, process_id, limit)
    else:
        query = """
            SELECT pe.*, sp.name as process_name
            FROM process_executions pe
            JOIN scheduled_processes sp ON pe.process_id = sp.id
            ORDER BY pe.scheduled_at DESC
            LIMIT $1
        """
        rows = await conn.fetch(query, limit)
    
    if not rows:
        print("No executions found.")
        return
    
    print("Recent Executions:")
    print(f"{'ID':<6} {'Process':<20} {'Status':<12} {'Scheduled':<16} {'Duration':<10} {'Exit':<5}")
    print("-" * 75)
    
    for row in rows:
        scheduled = row['scheduled_at'].strftime('%m-%d %H:%M:%S')
        duration = f"{row['duration_seconds']:.1f}s" if row['duration_seconds'] else "-"
        exit_code = str(row['exit_code']) if row['exit_code'] is not None else "-"
        
        print(f"{row['id']:<6} {row['process_name']:<20} {row['execution_status']:<12} "
              f"{scheduled:<16} {duration:<10} {exit_code:<5}")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage scheduled processes")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List scheduled processes")
    list_parser.add_argument("--enabled-only", action="store_true", help="Show only enabled processes")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new scheduled process")
    create_parser.add_argument("--name", required=True, help="Process name")
    create_parser.add_argument("--cron", required=True, help="Cron expression")
    create_parser.add_argument("--type", required=True, choices=["kafka_consumer", "data_pipeline", "scraper", "cleanup"], help="Process type")
    create_parser.add_argument("--service", required=True, help="Target service")
    create_parser.add_argument("--description", help="Process description")
    create_parser.add_argument("--config", help="Configuration JSON")
    create_parser.add_argument("--priority", type=int, default=5, help="Priority (1-10)")
    
    # Enable/Disable commands
    enable_parser = subparsers.add_parser("enable", help="Enable a process")
    enable_parser.add_argument("--id", type=int, required=True, help="Process ID")
    
    disable_parser = subparsers.add_parser("disable", help="Disable a process")
    disable_parser.add_argument("--id", type=int, required=True, help="Process ID")
    
    # Trigger command
    trigger_parser = subparsers.add_parser("trigger", help="Trigger manual execution")
    trigger_parser.add_argument("--id", type=int, required=True, help="Process ID")
    
    # Status command
    subparsers.add_parser("status", help="Show process status overview")
    
    # Executions command
    exec_parser = subparsers.add_parser("executions", help="Show execution history")
    exec_parser.add_argument("--process-id", type=int, help="Filter by process ID")
    exec_parser.add_argument("--limit", type=int, default=20, help="Number of executions to show")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        conn = await connect_db()
        
        if args.command == "list":
            await list_processes(conn, args.enabled_only)
        elif args.command == "create":
            await create_process(
                conn, args.name, args.cron, args.type, args.service,
                args.description, args.config, args.priority
            )
        elif args.command == "enable":
            await update_process_status(conn, args.id, True)
        elif args.command == "disable":
            await update_process_status(conn, args.id, False)
        elif args.command == "trigger":
            await trigger_execution(conn, args.id)
        elif args.command == "status":
            await show_status(conn)
        elif args.command == "executions":
            await show_executions(conn, args.process_id, args.limit)
        
        await conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())