"""API key authentication for the ingestion service."""

import structlog
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

logger = structlog.get_logger(__name__)

# API key header configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Hardcoded API key as requested
API_KEY = "apikeyhere"


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
) -> str:
    """Verify API key for authentication.

    Args:
    ----
        request: FastAPI request object
        api_key: API key from header

    Returns:
    -------
        Validated API key

    Raises:
    ------
        HTTPException: If API key is invalid or missing

    """
    # Skip auth for health check endpoints
    if request.url.path in [
        "/healthz",
        "/readyz",
        "/metrics",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]:
        return "health-check"

    # Check if API key is provided
    if not api_key:
        logger.warning(
            "Missing API key",
            path=request.url.path,
            method=request.method,
            client=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key
    if api_key != API_KEY:
        logger.warning(
            "Invalid API key",
            path=request.url.path,
            method=request.method,
            client=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.info(
        "API key validated",
        path=request.url.path,
        method=request.method,
    )

    return api_key
