#!/usr/bin/env python3
"""Test the database-driven configuration for kafka-to-db consumer."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg
from services.kafka_to_db_consumer.app.db_mapping_engine import DatabaseMappingEngine


async def test_db_config():
    """Test loading configuration from database."""
    
    # Get database URL
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://loom:loom@localhost:5432/loom"
    )
    
    print(f"Connecting to database: {database_url}")
    
    # Create connection pool
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    
    try:
        # Create mapping engine
        engine = DatabaseMappingEngine(pool)
        
        # Load configuration
        print("\nLoading configuration from database...")
        await engine.load_config()
        
        # Get supported topics
        topics = engine.get_supported_topics()
        print(f"\nFound {len(topics)} configured topics:")
        for i, topic in enumerate(topics[:10]):  # Show first 10
            print(f"  {i+1}. {topic}")
        if len(topics) > 10:
            print(f"  ... and {len(topics) - 10} more")
        
        # Test a specific topic mapping
        test_topic = "device.network.wifi.raw"
        print(f"\n\nTesting topic: {test_topic}")
        
        mapping = engine.get_topic_mapping(test_topic)
        if mapping:
            print(f"  Table: {mapping.get('table')}")
            print(f"  Upsert key: {mapping.get('upsert_key')}")
            print(f"  Field mappings ({len(mapping.get('field_mappings', {}))} fields):")
            for source, target in mapping.get('field_mappings', {}).items():
                data_type = mapping.get('data_types', {}).get(target, 'unknown')
                required = source in mapping.get('required_fields', [])
                print(f"    {source} → {target} ({data_type}){' [REQUIRED]' if required else ''}")
        else:
            print(f"  No mapping found for {test_topic}")
        
        # Test getting schema
        print(f"\n\nGetting schema for {test_topic}...")
        schema = await engine.get_topic_schema(test_topic)
        if schema:
            print(f"  Schema type: {schema.get('$schema', 'unknown')}")
            print(f"  Title: {schema.get('title', 'N/A')}")
            print(f"  Properties: {list(schema.get('properties', {}).keys())}")
        else:
            print("  No schema found")
            
        # Count total field mappings
        async with pool.acquire() as conn:
            total_mappings = await conn.fetchval(
                "SELECT COUNT(*) FROM topic_field_mappings"
            )
            total_configs = await conn.fetchval(
                "SELECT COUNT(*) FROM topic_table_configs"
            )
            
        print(f"\n\nDatabase statistics:")
        print(f"  Total topics configured: {len(topics)}")
        print(f"  Total table configs: {total_configs}")
        print(f"  Total field mappings: {total_mappings}")
        
    finally:
        await pool.close()
    
    print("\n✓ Database configuration test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_db_config())