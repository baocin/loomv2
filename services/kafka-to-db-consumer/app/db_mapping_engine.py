"""Database-driven mapping engine for kafka-to-db consumer.

This module provides a mapping engine that reads topic configurations
from the TimescaleDB schema management tables instead of YAML files.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
import structlog
from dateutil import parser as date_parser

from .mapping_engine import MappingEngine

logger = structlog.get_logger(__name__)


class DatabaseMappingEngine(MappingEngine):
    """Mapping engine that reads configuration from database instead of YAML."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize with database connection pool."""
        self.db_pool = db_pool
        self.config = {"topics": {}}
        self.config_loaded = False
        
    async def load_config(self) -> None:
        """Load mapping configuration from database."""
        try:
            async with self.db_pool.acquire() as conn:
                # Load topic table configurations
                rows = await conn.fetch('''
                    SELECT 
                        ttc.topic_name,
                        ttc.table_name,
                        ttc.upsert_key,
                        ttc.conflict_strategy,
                        kt.description
                    FROM topic_table_configs ttc
                    JOIN kafka_topics kt ON ttc.topic_name = kt.topic_name
                    WHERE kt.is_active = true
                ''')
                
                for row in rows:
                    topic_config = {
                        "table": row["table_name"],
                        "upsert_key": row["upsert_key"],
                        "conflict_strategy": row["conflict_strategy"],
                        "description": row["description"],
                        "field_mappings": {},
                        "data_types": {},
                        "transforms": {},
                        "required_fields": [],
                        "defaults": {}
                    }
                    
                    # Load field mappings
                    mappings = await conn.fetch('''
                        SELECT 
                            source_field_path,
                            target_column,
                            data_type,
                            transformation,
                            is_required
                        FROM topic_field_mappings
                        WHERE topic_name = $1
                        ORDER BY is_required DESC, target_column
                    ''', row["topic_name"])
                    
                    for mapping in mappings:
                        source = mapping["source_field_path"]
                        target = mapping["target_column"]
                        
                        topic_config["field_mappings"][source] = target
                        
                        if mapping["data_type"]:
                            topic_config["data_types"][target] = mapping["data_type"]
                            
                        if mapping["transformation"]:
                            topic_config["transforms"][target] = mapping["transformation"]
                            
                        if mapping["is_required"]:
                            topic_config["required_fields"].append(source)
                    
                    self.config["topics"][row["topic_name"]] = topic_config
                
                # Set global defaults
                self.config["defaults"] = {
                    "upsert_key": "device_id, timestamp",
                    "conflict_strategy": "ignore"
                }
                
                self.config_loaded = True
                
                logger.info(
                    "Loaded topic mapping configuration from database",
                    topics=len(self.config["topics"])
                )
                
        except Exception as e:
            logger.error(
                "Failed to load mapping configuration from database",
                error=str(e)
            )
            raise
    
    async def reload_config(self) -> None:
        """Reload configuration from database."""
        logger.info("Reloading topic mapping configuration from database")
        await self.load_config()
    
    def get_topic_mapping(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get mapping configuration for a specific topic."""
        if not self.config_loaded:
            logger.warning("Configuration not loaded from database")
            return None
            
        return self.config.get("topics", {}).get(topic)
    
    def get_supported_topics(self) -> List[str]:
        """Get list of all supported topics."""
        if not self.config_loaded:
            return []
            
        return list(self.config.get("topics", {}).keys())
    
    async def get_topic_schema(self, topic: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get JSON schema for a topic from database."""
        try:
            async with self.db_pool.acquire() as conn:
                if version:
                    schema_json = await conn.fetchval('''
                        SELECT schema_json
                        FROM kafka_topic_schemas
                        WHERE topic_name = $1 AND version = $2
                    ''', topic, version)
                else:
                    schema_json = await conn.fetchval('''
                        SELECT schema_json
                        FROM kafka_topic_schemas
                        WHERE topic_name = $1 AND is_current = true
                    ''', topic)
                
                if schema_json:
                    return json.loads(schema_json) if isinstance(schema_json, str) else schema_json
                    
        except Exception as e:
            logger.error(
                "Failed to get topic schema from database",
                topic=topic,
                version=version,
                error=str(e)
            )
            
        return None
    
    async def update_topic_stats(self, topic: str, records_processed: int) -> None:
        """Update processing statistics for a topic (optional feature)."""
        # This could be extended to track processing stats in the database
        pass