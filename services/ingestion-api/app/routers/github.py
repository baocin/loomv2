"""GitHub URL ingestion endpoints for OneFileLLM processing."""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import APIResponse, GitHubTask

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/github", tags=["github"])


@router.post("/ingest", response_model=APIResponse)
async def ingest_github_url(
    task: GitHubTask,
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Submit a GitHub URL for processing with OneFileLLM.

    This endpoint queues GitHub repositories, files, issues, or PRs for processing:
    - Repository: Aggregates all files matching patterns
    - File: Processes individual files
    - Issue/PR: Extracts discussion content and code changes

    Args:
    ----
        task: GitHub task with URL and processing parameters

    Returns:
    -------
        APIResponse with task status and message ID

    """
    try:
        # Send to GitHub processing queue
        await kafka_producer.send_message(
            topic="task.github.ingest",
            message=task,
        )

        logger.info(
            "GitHub ingestion task submitted",
            device_id=task.device_id,
            message_id=task.message_id,
            url=task.url,
            repository_type=task.repository_type,
            priority=task.priority,
        )

        return APIResponse(
            status="success",
            message_id=task.message_id,
            topic="task.github.ingest",
        )

    except Exception as e:
        logger.error(
            "Failed to submit GitHub ingestion task",
            device_id=task.device_id,
            url=task.url,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to submit GitHub task")


@router.post("/batch", response_model=APIResponse)
async def ingest_github_urls_batch(
    tasks: list[GitHubTask],
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Submit multiple GitHub URLs for processing in a batch.

    Args:
    ----
        tasks: List of GitHub processing tasks

    Returns:
    -------
        APIResponse with batch processing status

    """
    if len(tasks) > 20:  # Reasonable limit for GitHub processing
        raise HTTPException(
            status_code=400,
            detail="Batch size too large (max 20 GitHub URLs)",
        )

    successful = 0
    failed = 0
    errors = []

    for task in tasks:
        try:
            await kafka_producer.send_message(
                topic="task.github.ingest",
                message=task,
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(f"GitHub URL {task.url}: {e!s}")
            logger.error(
                "Failed to submit GitHub URL in batch",
                device_id=task.device_id,
                message_id=task.message_id,
                url=task.url,
                error=str(e),
            )

    logger.info(
        "Batch GitHub ingestion completed",
        total=len(tasks),
        successful=successful,
        failed=failed,
    )

    return APIResponse(
        status="success" if failed == 0 else "partial",
        topic="task.github.ingest",
        metadata={
            "successful": successful,
            "failed": failed,
            "errors": errors[:5],  # Limit error list
        },
    )
