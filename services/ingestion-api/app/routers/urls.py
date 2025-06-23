"""URL ingestion endpoints for processing tasks."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, HttpUrl

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import APIResponse, BaseMessage

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/urls", tags=["urls"])


class URLTask(BaseMessage):
    """URL processing task."""

    url: HttpUrl = Field(description="URL to process")
    task_type: str = Field(
        default="general",
        description="Type of processing (twitter, pdf, webpage, github)",
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)",
    )
    content_hint: str | None = Field(
        None,
        description="Hint about expected content type",
    )
    extract_options: dict[str, Any] = Field(
        default_factory=dict,
        description="Options for content extraction",
    )
    callback_webhook: HttpUrl | None = Field(
        None,
        description="Webhook URL for processing completion notification",
    )


@router.post("/ingest", response_model=APIResponse)
async def ingest_url(
    task: URLTask,
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Submit a URL for processing.

    This endpoint queues URLs for processing by specialized consumers:
    - Twitter/X posts and threads
    - PDF documents
    - Web pages and articles
    - GitHub repositories and files
    - General web content

    Args:
    ----
        task: URL task with processing parameters

    Returns:
    -------
        APIResponse with task status and message ID

    """
    try:
        # Send to URL processing queue
        await kafka_producer.send_message(
            topic="task.url.ingest",
            message=task,
        )

        logger.info(
            "URL ingestion task submitted",
            device_id=task.device_id,
            message_id=task.message_id,
            url=str(task.url),
            task_type=task.task_type,
            priority=task.priority,
        )

        return APIResponse(
            status="success",
            message_id=task.message_id,
            topic="task.url.ingest",
        )

    except Exception as e:
        logger.error(
            "Failed to submit URL ingestion task",
            device_id=task.device_id,
            url=str(task.url),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to submit URL task")


@router.post("/batch", response_model=APIResponse)
async def ingest_urls_batch(
    tasks: list[URLTask],
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Submit multiple URLs for processing in a batch.

    Args:
    ----
        tasks: List of URL processing tasks

    Returns:
    -------
        APIResponse with batch processing status

    """
    if len(tasks) > 50:  # Configurable limit
        raise HTTPException(
            status_code=400,
            detail="Batch size too large (max 50 URLs)",
        )

    successful = 0
    failed = 0
    errors = []

    for task in tasks:
        try:
            await kafka_producer.send_message(
                topic="task.url.ingest",
                message=task,
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(f"URL {task.url}: {e!s}")
            logger.error(
                "Failed to submit URL in batch",
                device_id=task.device_id,
                message_id=task.message_id,
                url=str(task.url),
                error=str(e),
            )

    logger.info(
        "Batch URL ingestion completed",
        total=len(tasks),
        successful=successful,
        failed=failed,
    )

    return APIResponse(
        status="success" if failed == 0 else "partial",
        topic="task.url.ingest",
        metadata={
            "successful": successful,
            "failed": failed,
            "errors": errors[:10],
        },  # Limit error list
    )
