"""Data collection modules for various macOS data sources."""

from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

logger = structlog.get_logger(__name__)


class BaseCollector(ABC):
    """Base class for all data collectors."""
    
    def __init__(self, api_client, interval: int):
        self.api_client = api_client
        self.interval = interval
        self._initialized = False
        self._last_collection = None
        self._collection_count = 0
        self._error_count = 0
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the collector."""
        pass
    
    @abstractmethod
    async def collect(self) -> bool:
        """Collect and send data. Return True if successful."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """Get collector status."""
        return {
            "initialized": self._initialized,
            "last_collection": self._last_collection,
            "collection_count": self._collection_count,
            "error_count": self._error_count,
            "interval": self.interval
        }