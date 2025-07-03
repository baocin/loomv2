"""REST endpoints for digital data ingestion."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import ClipboardData, WebAnalyticsData
from ..tracing import get_trace_context

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/digital", tags=["digital"])


@router.post("/clipboard", status_code=status.HTTP_201_CREATED)
async def ingest_clipboard_data(
    clipboard_data: ClipboardData,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest clipboard content data.

    Args:
    ----
        clipboard_data: Clipboard content data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        clipboard_data.trace_id = trace_context.get("trace_id")
        clipboard_data.services_encountered = trace_context.get(
            "services_encountered", []
        )

        await kafka_producer.send_digital_data(clipboard_data, "clipboard")

        logger.info(
            "Clipboard data ingested",
            device_id=clipboard_data.device_id,
            message_id=clipboard_data.message_id,
            content_type=clipboard_data.content_type,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": clipboard_data.message_id,
                "topic": "digital.clipboard.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest clipboard data",
            device_id=clipboard_data.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest clipboard data",
        )


@router.post("/web-analytics", status_code=status.HTTP_201_CREATED)
async def ingest_web_analytics_data(
    web_analytics: WebAnalyticsData,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Ingest web browsing analytics data.

    Args:
    ----
        web_analytics: Web analytics data

    Returns:
    -------
        Success response with message ID

    """
    try:
        # Get trace context and add to message
        trace_context = get_trace_context()
        web_analytics.trace_id = trace_context.get("trace_id")
        web_analytics.services_encountered = trace_context.get(
            "services_encountered", []
        )

        await kafka_producer.send_digital_data(web_analytics, "web_analytics")

        logger.info(
            "Web analytics data ingested",
            device_id=web_analytics.device_id,
            message_id=web_analytics.message_id,
            url=web_analytics.url,
            domain=web_analytics.domain,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": web_analytics.message_id,
                "topic": "digital.web_analytics.raw",
                "trace_id": trace_context.get("trace_id"),
                "services_encountered": trace_context.get("services_encountered", []),
            },
        )

    except Exception as e:
        logger.error(
            "Failed to ingest web analytics data",
            device_id=web_analytics.device_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest web analytics data",
        )
