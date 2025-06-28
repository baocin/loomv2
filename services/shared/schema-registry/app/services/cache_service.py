"""Redis-based caching service for schema registry."""

import json
import os
from typing import Any, Dict, Optional

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
    
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )
            
            # Test connection
            await self.ping()
            logger.info("Cache service initialized", redis_url=self.redis_url)
            
        except Exception as e:
            logger.error("Failed to initialize cache service", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Cache service closed")
    
    async def ping(self) -> bool:
        """Test Redis connectivity."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error("Cache ping failed", error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl
            
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            return False
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache."""
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error("Cache increment failed", key=key, error=str(e))
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.redis_client:
            return {"connected": False}
        
        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "memory_used": info.get("used_memory_human", "N/A"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"connected": False, "error": str(e)}