#!/usr/bin/env python3
"""
Setup script for Twitter extraction retry scheduled process.

This script creates a scheduled process that runs every 4 hours to find 
Twitter extractions with no extracted text and republish them to Kafka for retry.
"""

import asyncio
import json
import sys

import asyncpg


async def setup_twitter_retry_process():
    """Set up the Twitter extraction retry scheduled process."""
    
    database_url = "postgresql://loom:loom@localhost:5432/loom"
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check if process already exists
        existing = await conn.fetchval(
            "SELECT id FROM scheduled_processes WHERE name = 'twitter_extraction_retry'"
        )
        
        if existing:
            print(f"Twitter extraction retry process already exists with ID {existing}")
            
            # Optionally update the configuration
            update_choice = input("Do you want to update the configuration? (y/N): ").strip().lower()
            if update_choice == 'y':
                await update_process_config(conn, existing)
            
            await conn.close()
            return existing
        
        # Create the process
        process_config = {
            "batch_size": 100,
            "max_retry_attempts": 3,
            "min_age_hours": 2,  # Wait 2 hours before retrying
            "max_age_days": 7,   # Don't retry items older than 7 days
            "retry_topic": "task.url.ingest"
        }
        
        process_id = await conn.fetchval("""
            INSERT INTO scheduled_processes (
                name, 
                description, 
                cron_expression, 
                process_type, 
                target_service,
                configuration, 
                priority,
                enabled
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            'twitter_extraction_retry',
            'Retry failed Twitter extractions with no extracted text',
            '0 */4 * * *',  # Every 4 hours
            'retry_processor',
            'twitter-extraction-retry',
            process_config,
            2,  # High priority
            True
        )
        
        print(f"✅ Created Twitter extraction retry process with ID {process_id}")
        print(f"   Schedule: Every 4 hours")
        print(f"   Configuration: {json.dumps(process_config, indent=2)}")
        
        await conn.close()
        return process_id
        
    except Exception as e:
        print(f"❌ Error setting up Twitter extraction retry process: {e}")
        sys.exit(1)


async def update_process_config(conn: asyncpg.Connection, process_id: int):
    """Update the configuration of an existing process."""
    
    print("\nCurrent configuration options:")
    print("1. batch_size (default: 100) - Number of extractions to process per batch")
    print("2. max_retry_attempts (default: 3) - Maximum retry attempts per URL")
    print("3. min_age_hours (default: 2) - Minimum age in hours before retrying")
    print("4. max_age_days (default: 7) - Maximum age in days for retries")
    print("5. retry_topic (default: task.url.ingest) - Kafka topic for retry messages")
    
    config = {}
    
    # Get user input for configuration
    batch_size = input("\nBatch size (100): ").strip()
    if batch_size:
        config["batch_size"] = int(batch_size)
    else:
        config["batch_size"] = 100
    
    max_retry = input("Max retry attempts (3): ").strip()
    if max_retry:
        config["max_retry_attempts"] = int(max_retry)
    else:
        config["max_retry_attempts"] = 3
    
    min_age = input("Min age hours (2): ").strip()
    if min_age:
        config["min_age_hours"] = int(min_age)
    else:
        config["min_age_hours"] = 2
    
    max_age = input("Max age days (7): ").strip()
    if max_age:
        config["max_age_days"] = int(max_age)
    else:
        config["max_age_days"] = 7
    
    retry_topic = input("Retry topic (task.url.ingest): ").strip()
    if retry_topic:
        config["retry_topic"] = retry_topic
    else:
        config["retry_topic"] = "task.url.ingest"
    
    # Update cron expression if desired
    cron_expr = input("Cron expression (0 */4 * * * for every 4 hours): ").strip()
    if not cron_expr:
        cron_expr = "0 */4 * * *"
    
    # Update the process
    await conn.execute("""
        UPDATE scheduled_processes 
        SET configuration = $1, cron_expression = $2, updated_at = NOW()
        WHERE id = $3
    """, config, cron_expr, process_id)
    
    print(f"✅ Updated process configuration")
    print(f"   Schedule: {cron_expr}")
    print(f"   Configuration: {json.dumps(config, indent=2)}")


async def show_process_status():
    """Show the status of the Twitter extraction retry process."""
    
    database_url = "postgresql://loom:loom@localhost:5432/loom"
    
    try:
        conn = await asyncpg.connect(database_url)
        
        process = await conn.fetchrow("""
            SELECT sp.*, 
                   latest.execution_status as last_status,
                   latest.completed_at as last_execution,
                   latest.error_message as last_error
            FROM scheduled_processes sp
            LEFT JOIN LATERAL (
                SELECT execution_status, completed_at, error_message
                FROM process_executions pe
                WHERE pe.process_id = sp.id
                ORDER BY pe.scheduled_at DESC
                LIMIT 1
            ) latest ON true
            WHERE sp.name = 'twitter_extraction_retry'
        """)
        
        if not process:
            print("❌ Twitter extraction retry process not found")
            return
        
        print(f"\n📊 Twitter Extraction Retry Process Status")
        print(f"   ID: {process['id']}")
        print(f"   Name: {process['name']}")
        print(f"   Enabled: {'✅' if process['enabled'] else '❌'}")
        print(f"   Schedule: {process['cron_expression']}")
        print(f"   Priority: {process['priority']}")
        print(f"   Last Status: {process['last_status'] or 'Never run'}")
        print(f"   Last Execution: {process['last_execution'] or 'Never'}")
        
        if process['last_error']:
            print(f"   Last Error: {process['last_error']}")
        
        config = process['configuration']
        print(f"\n⚙️ Configuration:")
        for key, value in config.items():
            print(f"   {key}: {value}")
        
        # Show recent executions
        executions = await conn.fetch("""
            SELECT execution_status, scheduled_at, started_at, completed_at, 
                   duration_seconds, error_message
            FROM process_executions 
            WHERE process_id = $1 
            ORDER BY scheduled_at DESC 
            LIMIT 5
        """, process['id'])
        
        if executions:
            print(f"\n📈 Recent Executions:")
            for exec in executions:
                status_icon = {
                    'completed': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'scheduled': '⏰'
                }.get(exec['execution_status'], '❓')
                
                duration = f" ({exec['duration_seconds']:.1f}s)" if exec['duration_seconds'] else ""
                print(f"   {status_icon} {exec['scheduled_at'].strftime('%Y-%m-%d %H:%M')} - {exec['execution_status']}{duration}")
                
                if exec['error_message']:
                    print(f"      Error: {exec['error_message'][:100]}...")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error checking process status: {e}")


async def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Twitter extraction retry process")
    parser.add_argument("action", choices=["setup", "status"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "setup":
        await setup_twitter_retry_process()
    elif args.action == "status":
        await show_process_status()


if __name__ == "__main__":
    asyncio.run(main())