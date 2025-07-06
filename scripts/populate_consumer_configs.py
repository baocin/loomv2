#!/usr/bin/env python3
"""
Script to populate consumer configurations for services that don't have them yet.
This analyzes existing services and suggests appropriate Kafka consumer settings.
"""

import asyncio
import asyncpg
import argparse
from typing import Dict, Any, List, Tuple

# Service categories with their typical characteristics
SERVICE_PROFILES = {
    "vision": {
        "description": "GPU-intensive vision/image processing",
        "max_poll_records": 1,
        "session_timeout_ms": 300000,  # 5 min
        "max_poll_interval_ms": 600000,  # 10 min
        "max_partition_fetch_bytes": 52428800,  # 50MB
        "examples": ["moondream", "minicpm", "face", "yolo", "vision"],
    },
    "audio_heavy": {
        "description": "Audio processing with AI models",
        "max_poll_records": 10,
        "session_timeout_ms": 120000,  # 2 min
        "max_poll_interval_ms": 300000,  # 5 min
        "max_partition_fetch_bytes": 10485760,  # 10MB
        "examples": ["stt", "kyutai", "whisper", "transcr"],
    },
    "audio_light": {
        "description": "Simple audio processing",
        "max_poll_records": 500,
        "session_timeout_ms": 30000,  # 30 sec
        "max_poll_interval_ms": 60000,  # 1 min
        "examples": ["vad", "audio-filter", "audio-chunk"],
    },
    "sensor": {
        "description": "High-volume sensor data processing",
        "max_poll_records": 1000,
        "session_timeout_ms": 30000,
        "max_poll_interval_ms": 60000,
        "partition_assignment_strategy": "sticky",
        "examples": ["accelerometer", "motion", "step", "activity", "sensor"],
    },
    "llm": {
        "description": "Large language model processing",
        "max_poll_records": 1,
        "session_timeout_ms": 600000,  # 10 min
        "max_poll_interval_ms": 1200000,  # 20 min
        "request_timeout_ms": 1205000,
        "examples": ["mistral", "llama", "gemma", "reasoning", "onefilellm"],
    },
    "network_io": {
        "description": "External API calls and web scraping",
        "max_poll_records": 5,
        "session_timeout_ms": 180000,  # 3 min
        "max_poll_interval_ms": 360000,  # 6 min
        "retry_backoff_ms": 1000,
        "fetch_max_wait_ms": 5000,
        "examples": [
            "geocod",
            "scraper",
            "fetcher",
            "url-processor",
            "twitter",
            "email",
        ],
    },
    "database": {
        "description": "Database writing and batch processing",
        "max_poll_records": 1000,
        "session_timeout_ms": 60000,
        "max_poll_interval_ms": 120000,
        "enable_auto_commit": True,
        "examples": ["writer", "saver", "db-consumer", "timescale"],
    },
    "embedding": {
        "description": "Text embedding and vector processing",
        "max_poll_records": 20,
        "session_timeout_ms": 120000,
        "max_poll_interval_ms": 240000,
        "examples": ["embed", "vector", "nomic"],
    },
    "default": {
        "description": "Default configuration for unmatched services",
        "max_poll_records": 100,
        "session_timeout_ms": 60000,
        "max_poll_interval_ms": 300000,
        "examples": [],
    },
}


def categorize_service(service_name: str) -> Tuple[str, Dict[str, Any]]:
    """Categorize a service based on its name and return appropriate config."""
    service_lower = service_name.lower()

    for category, profile in SERVICE_PROFILES.items():
        for example in profile["examples"]:
            if example in service_lower:
                return category, profile

    return "default", SERVICE_PROFILES["default"]


async def get_existing_services(conn: asyncpg.Connection) -> List[Dict[str, Any]]:
    """Get all pipeline services that don't have consumer configs yet."""
    query = """
        SELECT
            ps.service_name,
            ps.service_type,
            ps.replicas,
            ps.processing_timeout_seconds,
            ps.flow_name,
            COUNT(DISTINCT pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as input_topic_count,
            STRING_AGG(DISTINCT pst.topic_name, ', ' ORDER BY pst.topic_name) FILTER (WHERE pst.topic_role = 'input') as input_topics
        FROM pipeline_stages ps
        LEFT JOIN pipeline_stage_topics pst ON ps.id = pst.stage_id
        LEFT JOIN pipeline_consumer_configs pcc ON ps.service_name = pcc.service_name
        WHERE pcc.service_name IS NULL
            AND ps.service_type IN ('processor', 'enricher', 'analyzer', 'writer')
        GROUP BY ps.service_name, ps.service_type, ps.replicas, ps.processing_timeout_seconds, ps.flow_name
        ORDER BY ps.service_name
    """

    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def insert_consumer_config(
    conn: asyncpg.Connection, service: Dict[str, Any], profile: Dict[str, Any]
) -> None:
    """Insert a consumer configuration for a service."""
    # Build consumer group ID
    group_id = f"loom-{service['service_name']}"

    # Build the config
    config = {
        "service_name": service["service_name"],
        "consumer_group_id": group_id,
        "max_poll_records": profile.get("max_poll_records", 100),
        "session_timeout_ms": profile.get("session_timeout_ms", 60000),
        "max_poll_interval_ms": profile.get("max_poll_interval_ms", 300000),
        "heartbeat_interval_ms": profile.get("session_timeout_ms", 60000) // 3,
        "partition_assignment_strategy": profile.get(
            "partition_assignment_strategy", "range"
        ),
        "enable_auto_commit": profile.get("enable_auto_commit", False),
        "auto_commit_interval_ms": 5000,
        "auto_offset_reset": "earliest",
        "fetch_min_bytes": 1,
        "fetch_max_wait_ms": profile.get("fetch_max_wait_ms", 500),
        "max_partition_fetch_bytes": profile.get("max_partition_fetch_bytes", 1048576),
        "request_timeout_ms": profile.get("request_timeout_ms", 305000),
        "retry_backoff_ms": profile.get("retry_backoff_ms", 100),
        "reconnect_backoff_ms": 50,
        "reconnect_backoff_max_ms": 1000,
    }

    # Build INSERT query
    columns = list(config.keys())
    values = [config[col] for col in columns]
    placeholders = [f"${i+1}" for i in range(len(columns))]

    query = f"""
        INSERT INTO pipeline_consumer_configs ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        ON CONFLICT (service_name) DO NOTHING
    """

    await conn.execute(query, *values)


async def main(database_url: str, dry_run: bool = False):
    """Main function to populate consumer configurations."""
    conn = await asyncpg.connect(database_url)

    try:
        # Get services without configs
        services = await get_existing_services(conn)

        if not services:
            print("All services already have consumer configurations!")
            return

        print(f"Found {len(services)} services without consumer configurations:\n")

        # Categorize and display recommendations
        recommendations = []
        for service in services:
            category, profile = categorize_service(service["service_name"])
            recommendations.append((service, category, profile))

            print(f"Service: {service['service_name']}")
            print(f"  Type: {service['service_type']}")
            print(f"  Category: {category} ({profile['description']})")
            print(f"  Input Topics: {service['input_topics'] or 'None'}")
            print("  Suggested Config:")
            print(f"    - max_poll_records: {profile.get('max_poll_records', 100)}")
            print(
                f"    - session_timeout_ms: {profile.get('session_timeout_ms', 60000)}"
            )
            print(
                f"    - max_poll_interval_ms: {profile.get('max_poll_interval_ms', 300000)}"
            )
            if "max_partition_fetch_bytes" in profile:
                print(
                    f"    - max_partition_fetch_bytes: {profile['max_partition_fetch_bytes']} ({profile['max_partition_fetch_bytes'] // 1048576}MB)"
                )
            print()

        if dry_run:
            print("DRY RUN - No changes made")
            return

        # Ask for confirmation
        response = input(
            f"\nProceed with creating {len(recommendations)} consumer configurations? (y/N): "
        )
        if response.lower() != "y":
            print("Cancelled")
            return

        # Insert configurations
        print("\nCreating consumer configurations...")
        created = 0
        for service, category, profile in recommendations:
            try:
                await insert_consumer_config(conn, service, profile)
                created += 1
                print(f"✓ Created config for {service['service_name']} ({category})")
            except Exception as e:
                print(f"✗ Failed to create config for {service['service_name']}: {e}")

        print(f"\nCreated {created} consumer configurations")

        # Show monitoring query
        if created > 0:
            print("\nTo monitor these consumers, run:")
            print("  SELECT * FROM v_consumer_config_monitoring;")
            print("\nTo check for lag alerts:")
            print("  SELECT * FROM v_consumer_lag_alerts;")

    finally:
        await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate Kafka consumer configurations"
    )
    parser.add_argument(
        "--database-url",
        default="postgresql://loom:loom@localhost:5432/loom",
        help="PostgreSQL connection URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes",
    )

    args = parser.parse_args()

    asyncio.run(main(args.database_url, args.dry_run))
