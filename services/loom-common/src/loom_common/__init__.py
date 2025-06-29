"""
Loom Common - Shared utilities for Loom v2 services
"""

__version__ = "0.1.0"

from loom_common.config import BaseSettings
from loom_common.logging import setup_logging

__all__ = ["BaseSettings", "setup_logging"]
