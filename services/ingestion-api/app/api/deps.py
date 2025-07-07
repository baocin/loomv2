"""API dependencies."""

from app.database import db_manager


async def get_db():
    """Get database connection."""
    return db_manager.database