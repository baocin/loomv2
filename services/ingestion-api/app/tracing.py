"""Distributed tracing utilities for request correlation."""

import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variables for trace information
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")
services_encountered_context: ContextVar[list[str]] = ContextVar(
    "services_encountered",
    default=[],
)

logger = structlog.get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to add trace ID and service tracking to all requests."""

    def __init__(self, app: Any, service_name: str = "ingestion-api") -> None:
        """Initialize tracing middleware.

        Args:
        ----
            app: FastAPI application instance
            service_name: Name of this service for tracking

        """
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with distributed tracing."""
        # Extract or generate trace ID
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("x-trace-id")
            or str(uuid.uuid4())
        )

        # Extract existing services from header or initialize
        services_header = request.headers.get("X-Services-Encountered", "")
        services_encountered = services_header.split(",") if services_header else []

        # Add current service to the list
        if self.service_name not in services_encountered:
            services_encountered.append(self.service_name)

        # Set context variables
        trace_id_context.set(trace_id)
        services_encountered_context.set(services_encountered)

        # Add to request state for easy access
        request.state.trace_id = trace_id
        request.state.services_encountered = services_encountered

        # Log request start
        logger.info(
            "Request started",
            trace_id=trace_id,
            services_encountered=services_encountered,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Process request
        response = await call_next(request)

        # Add trace headers to response
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Services-Encountered"] = ",".join(services_encountered)

        # Log request completion
        logger.info(
            "Request completed",
            trace_id=trace_id,
            services_encountered=services_encountered,
            status_code=response.status_code,
            method=request.method,
            path=request.url.path,
        )

        return response


def get_trace_id() -> str:
    """Get the current trace ID from context."""
    return trace_id_context.get("")


def get_services_encountered() -> list[str]:
    """Get the list of services encountered from context."""
    return services_encountered_context.get([])


def add_service_to_trace(service_name: str) -> None:
    """Add a service to the current trace's service list."""
    services = services_encountered_context.get([])
    if service_name not in services:
        services = services + [service_name]
        services_encountered_context.set(services)


def get_trace_context() -> dict[str, Any]:
    """Get complete trace context for logging and message headers."""
    return {
        "trace_id": get_trace_id(),
        "services_encountered": get_services_encountered(),
    }


def create_child_trace_context(parent_trace_id: str, parent_services: list[str]) -> str:
    """Create a new trace context inheriting from parent.

    Args:
    ----
        parent_trace_id: The parent request's trace ID
        parent_services: List of services the parent request encountered

    Returns:
    -------
        New trace ID for the child operation

    """
    # Generate new trace ID but maintain service chain
    child_trace_id = str(uuid.uuid4())

    # Inherit parent services
    services_encountered_context.set(parent_services.copy())
    trace_id_context.set(child_trace_id)

    return child_trace_id
