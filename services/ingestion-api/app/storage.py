"""Database storage module for persisting Kafka message data."""

import structlog
from datetime import datetime
from typing import Any, Dict

import asyncpg
from .config import settings

logger = structlog.get_logger(__name__)


class DatabaseStorage:
    """Manages database connections and data storage operations."""

    def __init__(self) -> None:
        """Initialize database storage."""
        self._pool: asyncpg.Pool = None

    async def start(self) -> None:
        """Initialize database connection pool."""
        try:
            # Create connection pool
            self._pool = await asyncpg.create_pool(
                host="localhost",
                port=5432,
                user="loom",
                password="loom",
                database="loom",
                min_size=2,
                max_size=10,
                command_timeout=30,
            )

            # Ensure tables exist
            await self._ensure_tables_exist()

            logger.info("Database storage initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize database storage", error=str(e))
            raise

    async def stop(self) -> None:
        """Close database connection pool."""
        if self._pool:
            try:
                await self._pool.close()
                logger.info("Database storage stopped")
            except Exception as e:
                logger.error("Error stopping database storage", error=str(e))

    async def _ensure_tables_exist(self) -> None:
        """Create required tables if they don't exist."""
        async with self._pool.acquire() as connection:
            # Create device_lock_states table
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS device_lock_states (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    is_locked BOOLEAN NOT NULL,
                    lock_type VARCHAR(50),
                    lock_timestamp TIMESTAMP WITH TIME ZONE,
                    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes for device_lock_states
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_lock_states_device_id 
                ON device_lock_states (device_id);
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_lock_states_timestamp 
                ON device_lock_states (timestamp);
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_lock_states_created_at 
                ON device_lock_states (created_at);
            """)

            # Create other state tables for consistency
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS device_power_states (
                    id SERIAL PRIMARY KEY,
                    device_id VARCHAR(255) NOT NULL,
                    message_id VARCHAR(255) UNIQUE NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    battery_level FLOAT NOT NULL,
                    is_charging BOOLEAN NOT NULL,
                    power_source VARCHAR(50),
                    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes for device_power_states
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_power_states_device_id 
                ON device_power_states (device_id);
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_power_states_timestamp 
                ON device_power_states (timestamp);
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_device_power_states_created_at 
                ON device_power_states (created_at);
            """)

            logger.info("Database tables ensured to exist")

    async def store_lock_state(self, message_data: Dict[str, Any]) -> bool:
        """Store lock state data in the database.
        
        Args:
        ----
            message_data: Lock state message from Kafka
            
        Returns:
        -------
            True if successfully stored, False otherwise
        """
        try:
            async with self._pool.acquire() as connection:
                await connection.execute("""
                    INSERT INTO device_lock_states (
                        device_id, message_id, timestamp, is_locked, 
                        lock_type, lock_timestamp, schema_version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (message_id) DO NOTHING
                """, 
                    message_data["device_id"],
                    message_data["message_id"],
                    datetime.fromisoformat(message_data["timestamp"].replace("Z", "+00:00")),
                    message_data["is_locked"],
                    message_data.get("lock_type"),
                    datetime.fromisoformat(message_data["lock_timestamp"].replace("Z", "+00:00")) if message_data.get("lock_timestamp") else None,
                    message_data.get("schema_version", "1.0")
                )

                logger.info(
                    "Lock state stored successfully",
                    device_id=message_data["device_id"],
                    message_id=message_data["message_id"],
                    is_locked=message_data["is_locked"]
                )
                return True

        except Exception as e:
            logger.error(
                "Failed to store lock state",
                device_id=message_data.get("device_id"),
                message_id=message_data.get("message_id"),
                error=str(e)
            )
            return False

    async def store_power_state(self, message_data: Dict[str, Any]) -> bool:
        """Store power state data in the database.
        
        Args:
        ----
            message_data: Power state message from Kafka
            
        Returns:
        -------
            True if successfully stored, False otherwise
        """
        try:
            async with self._pool.acquire() as connection:
                await connection.execute("""
                    INSERT INTO device_power_states (
                        device_id, message_id, timestamp, battery_level, 
                        is_charging, power_source, schema_version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (message_id) DO NOTHING
                """, 
                    message_data["device_id"],
                    message_data["message_id"],
                    datetime.fromisoformat(message_data["timestamp"].replace("Z", "+00:00")),
                    message_data["battery_level"],
                    message_data["is_charging"],
                    message_data.get("power_source"),
                    message_data.get("schema_version", "1.0")
                )

                logger.info(
                    "Power state stored successfully",
                    device_id=message_data["device_id"],
                    message_id=message_data["message_id"],
                    battery_level=message_data["battery_level"]
                )
                return True

        except Exception as e:
            logger.error(
                "Failed to store power state",
                device_id=message_data.get("device_id"),
                message_id=message_data.get("message_id"),
                error=str(e)
            )
            return False

    @property
    def is_connected(self) -> bool:
        """Check if database pool is available."""
        return self._pool is not None and not self._pool._closed


# Global storage instance
database_storage = DatabaseStorage()