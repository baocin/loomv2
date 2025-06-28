"""Schema management service for loading and validating JSON schemas."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import jsonschema
import structlog

from .cache_service import CacheService
from ..models import SchemaInfo, SchemaVersion

logger = structlog.get_logger(__name__)


class SchemaManager:
    """Manages JSON schemas and validation."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.schema_stats: Dict[str, int] = {}
        self.schema_path = os.getenv("SCHEMA_PATH", "/app/schemas")
        
    async def initialize(self) -> None:
        """Initialize schema manager by loading schemas."""
        await self._load_schemas()
        logger.info(
            "Schema manager initialized", 
            schemas_loaded=len(self.schemas),
            schema_path=self.schema_path
        )
    
    async def _load_schemas(self) -> None:
        """Load schemas from filesystem."""
        try:
            schema_dir = Path(self.schema_path)
            if not schema_dir.exists():
                logger.warning("Schema directory not found", path=self.schema_path)
                return
            
            # Load schemas recursively
            for schema_file in schema_dir.rglob("*.json"):
                try:
                    await self._load_schema_file(schema_file)
                except Exception as e:
                    logger.error(
                        "Failed to load schema file",
                        file=str(schema_file),
                        error=str(e)
                    )
                    
        except Exception as e:
            logger.error("Failed to load schemas", error=str(e))
            raise
    
    async def _load_schema_file(self, schema_file: Path) -> None:
        """Load a single schema file."""
        try:
            async with aiofiles.open(schema_file, 'r') as f:
                content = await f.read()
                schema_data = json.loads(content)
            
            # Extract schema name from file path
            relative_path = schema_file.relative_to(Path(self.schema_path))
            schema_name = str(relative_path).replace('.json', '').replace('/', '.')
            
            # Validate the schema itself
            jsonschema.Draft202012Validator.check_schema(schema_data)
            
            # Store schema
            self.schemas[schema_name] = {
                "schema": schema_data,
                "file_path": str(schema_file),
                "loaded_at": datetime.utcnow(),
                "version": schema_data.get("version", "1.0"),
                "description": schema_data.get("description", ""),
            }
            
            # Cache the schema
            await self.cache_service.set(
                f"schema:{schema_name}",
                self.schemas[schema_name],
                ttl=7200  # 2 hours
            )
            
            logger.debug("Schema loaded", schema_name=schema_name)
            
        except Exception as e:
            logger.error(
                "Failed to load schema file",
                file=str(schema_file),
                error=str(e)
            )
            raise
    
    async def validate(self, schema_name: str, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data against a schema."""
        try:
            # Get schema from cache first, then from memory
            schema_info = await self._get_schema(schema_name)
            if not schema_info:
                return False, [f"Schema '{schema_name}' not found"]
            
            # Perform validation
            validator = jsonschema.Draft202012Validator(schema_info["schema"])
            errors = []
            
            for error in validator.iter_errors(data):
                errors.append(f"{error.json_path}: {error.message}")
            
            is_valid = len(errors) == 0
            
            # Update usage statistics
            await self._update_usage_stats(schema_name)
            
            return is_valid, errors
            
        except Exception as e:
            logger.error(
                "Schema validation failed",
                schema_name=schema_name,
                error=str(e)
            )
            return False, [f"Validation error: {str(e)}"]
    
    async def _get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get schema from cache or memory."""
        # Try cache first
        cached_schema = await self.cache_service.get(f"schema:{schema_name}")
        if cached_schema:
            return cached_schema
        
        # Fallback to memory
        if schema_name in self.schemas:
            schema_info = self.schemas[schema_name]
            # Update cache
            await self.cache_service.set(f"schema:{schema_name}", schema_info)
            return schema_info
        
        return None
    
    async def _update_usage_stats(self, schema_name: str) -> None:
        """Update usage statistics for a schema."""
        try:
            # Update in-memory stats
            self.schema_stats[schema_name] = self.schema_stats.get(schema_name, 0) + 1
            
            # Update cached stats
            await self.cache_service.increment(f"usage:{schema_name}")
            
        except Exception as e:
            logger.error(
                "Failed to update usage stats",
                schema_name=schema_name,
                error=str(e)
            )
    
    async def list_schemas(self) -> List[str]:
        """List all available schemas."""
        return list(self.schemas.keys())
    
    async def get_schema_info(self, schema_name: str) -> Optional[SchemaInfo]:
        """Get detailed information about a schema."""
        schema_info = await self._get_schema(schema_name)
        if not schema_info:
            return None
        
        usage_count = self.schema_stats.get(schema_name, 0)
        cached_usage = await self.cache_service.get(f"usage:{schema_name}")
        if cached_usage:
            usage_count = max(usage_count, cached_usage)
        
        return SchemaInfo(
            name=schema_name,
            version=schema_info.get("version", "1.0"),
            description=schema_info.get("description", ""),
            schema=schema_info["schema"],
            created_at=schema_info["loaded_at"],
            updated_at=schema_info["loaded_at"],
            usage_count=usage_count
        )
    
    async def get_schema_versions(self, schema_name: str) -> List[SchemaVersion]:
        """Get all versions of a schema."""
        # For now, return single version (could be extended for multi-version support)
        schema_info = await self._get_schema(schema_name)
        if not schema_info:
            return []
        
        return [
            SchemaVersion(
                version=schema_info.get("version", "1.0"),
                created_at=schema_info["loaded_at"],
                compatibility="FULL",
                changes=[]
            )
        ]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        cache_stats = await self.cache_service.get_stats()
        
        return {
            "schemas_loaded": len(self.schemas),
            "total_validations": sum(self.schema_stats.values()),
            "most_used_schemas": sorted(
                self.schema_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "cache": cache_stats
        }