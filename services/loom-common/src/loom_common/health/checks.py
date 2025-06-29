"""
Health check implementations
"""

import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List

import asyncpg
import structlog
from aiokafka import AIOKafkaConsumer

logger = structlog.get_logger(__name__)


class HealthChecker:
    """Configurable health checker for services"""

    def __init__(self):
        self.checks: List[Callable[[], Awaitable[Dict[str, Any]]]] = []

    def add_check(self, name: str, check_func: Callable[[], Awaitable[bool]]) -> None:
        """
        Add a health check

        Args:
            name: Name of the check
            check_func: Async function that returns True if healthy
        """

        async def wrapped_check() -> Dict[str, Any]:
            try:
                start_time = datetime.utcnow()
                result = await check_func()
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                return {
                    "name": name,
                    "status": "healthy" if result else "unhealthy",
                    "duration_ms": duration_ms,
                }
            except Exception as e:
                logger.error(f"Health check failed: {name}", error=str(e))
                return {
                    "name": name,
                    "status": "unhealthy",
                    "error": str(e),
                }

        self.checks.append(wrapped_check)

    async def check_health(self) -> Dict[str, Any]:
        """
        Run all health checks and return aggregated result

        Returns:
            Dictionary with overall status and individual check results
        """
        if not self.checks:
            return {
                "ready": True,
                "status": "healthy",
                "checks": [],
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Run all checks concurrently
        results = await asyncio.gather(*[check() for check in self.checks])

        # Determine overall status
        all_healthy = all(r["status"] == "healthy" for r in results)

        return {
            "ready": all_healthy,
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": results,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def kafka_health_check(bootstrap_servers: str, timeout: float = 5.0) -> bool:
    """
    Check if Kafka is reachable

    Args:
        bootstrap_servers: Kafka broker addresses
        timeout: Connection timeout in seconds

    Returns:
        True if Kafka is healthy
    """
    consumer = None
    try:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=int(timeout * 1000),
            connections_max_idle_ms=int(timeout * 1000),
        )
        await asyncio.wait_for(consumer.start(), timeout=timeout)
        # Get metadata to verify connection
        await consumer.list_topics()
        return True
    except Exception as e:
        logger.warning(f"Kafka health check failed: {e}")
        return False
    finally:
        if consumer:
            try:
                await consumer.stop()
            except Exception:
                pass


async def database_health_check(database_url: str, timeout: float = 5.0) -> bool:
    """
    Check if database is reachable

    Args:
        database_url: PostgreSQL connection URL
        timeout: Connection timeout in seconds

    Returns:
        True if database is healthy
    """
    conn = None
    try:
        conn = await asyncio.wait_for(asyncpg.connect(database_url), timeout=timeout)
        # Run simple query
        await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return False
    finally:
        if conn:
            try:
                await conn.close()
            except Exception:
                pass
