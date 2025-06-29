"""
FastAPI health check router
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from loom_common.health.checks import HealthChecker


def create_health_router(
    health_checker: Optional[HealthChecker] = None, include_metrics: bool = True
) -> APIRouter:
    """
    Create a FastAPI router with standard health endpoints

    Args:
        health_checker: Optional custom health checker
        include_metrics: Whether to include Prometheus metrics endpoint

    Returns:
        Configured APIRouter
    """
    router = APIRouter(tags=["health"])

    if health_checker is None:
        health_checker = HealthChecker()

    @router.get("/healthz")
    async def liveness() -> Dict[str, str]:
        """
        Kubernetes liveness probe endpoint.
        Returns 200 if the service is alive.
        """
        return {"status": "ok"}

    @router.get("/readyz")
    async def readiness() -> Dict[str, Any]:
        """
        Kubernetes readiness probe endpoint.
        Returns 200 if the service is ready to accept traffic.
        """
        result = await health_checker.check_health()

        if not result["ready"]:
            return Response(
                content=result, status_code=503, media_type="application/json"
            )

        return result

    if include_metrics:

        @router.get("/metrics")
        async def metrics() -> Response:
            """
            Prometheus metrics endpoint
            """
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return router
