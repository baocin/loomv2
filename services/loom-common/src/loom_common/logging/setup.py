"""
Structured logging configuration
"""

import logging
import sys
from typing import Optional

import structlog
from structlog.types import EventDict, Processor

from loom_common.config import BaseSettings


def setup_logging(
    service_name: str,
    settings: Optional[BaseSettings] = None,
    correlation_id_var: Optional[str] = None,
) -> structlog.BoundLogger:
    """
    Configure structured logging for a service

    Args:
        service_name: Name of the service for log identification
        settings: Optional settings object (will create default if not provided)
        correlation_id_var: Optional context var name for correlation ID

    Returns:
        Configured logger instance
    """
    if settings is None:
        settings = BaseSettings(service_name=service_name)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Processors for structlog
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add service name to all logs
    def add_service_name(logger, method_name, event_dict: EventDict) -> EventDict:
        event_dict["service"] = service_name
        event_dict["environment"] = settings.environment
        return event_dict

    processors.append(add_service_name)

    # Add correlation ID if configured
    if correlation_id_var:
        from contextvars import ContextVar

        correlation_id: ContextVar[Optional[str]] = ContextVar(
            correlation_id_var, default=None
        )

        def add_correlation_id(logger, method_name, event_dict: EventDict) -> EventDict:
            cid = correlation_id.get()
            if cid:
                event_dict["correlation_id"] = cid
            return event_dict

        processors.append(add_correlation_id)

    # JSON or console rendering based on environment
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(service_name)


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance

    Args:
        name: Optional logger name (defaults to caller's module)

    Returns:
        Logger instance
    """
    return structlog.get_logger(name)
