"""Document upload endpoints for OneFileLLM processing."""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import APIResponse, DocumentTask

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=APIResponse)
async def upload_document(
    task: DocumentTask,
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Upload a document for processing with OneFileLLM.

    This endpoint accepts various document types for processing:
    - PDF documents
    - Word documents (docx)
    - Text files
    - Markdown files
    - HTML files
    - Other text-based formats

    Args:
    ----
        task: Document upload task with file data and processing parameters

    Returns:
    -------
        APIResponse with task status and message ID

    """
    try:
        # Send to document processing queue
        await kafka_producer.send_message(
            topic="task.document.ingest",
            message=task,
        )

        logger.info(
            "Document upload task submitted",
            device_id=task.device_id,
            message_id=task.message_id,
            filename=task.filename,
            document_type=task.document_type,
            file_size=task.file_size,
            priority=task.priority,
        )

        return APIResponse(
            status="success",
            message_id=task.message_id,
            topic="task.document.ingest",
        )

    except Exception as e:
        logger.error(
            "Failed to submit document upload task",
            device_id=task.device_id,
            filename=task.filename,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to submit document task")


@router.post("/batch", response_model=APIResponse)
async def upload_documents_batch(
    tasks: list[DocumentTask],
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Upload multiple documents for processing in a batch.

    Args:
    ----
        tasks: List of document upload tasks

    Returns:
    -------
        APIResponse with batch processing status

    """
    if len(tasks) > 10:  # Conservative limit for document processing
        raise HTTPException(
            status_code=400,
            detail="Batch size too large (max 10 documents)",
        )

    # Check total batch size
    total_size = sum(task.file_size for task in tasks)
    max_batch_size = 500 * 1024 * 1024  # 500MB total
    if total_size > max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Total batch size exceeds {max_batch_size // (1024*1024)}MB limit",
        )

    successful = 0
    failed = 0
    errors = []

    for task in tasks:
        try:
            await kafka_producer.send_message(
                topic="task.document.ingest",
                message=task,
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(f"Document {task.filename}: {e!s}")
            logger.error(
                "Failed to submit document in batch",
                device_id=task.device_id,
                message_id=task.message_id,
                filename=task.filename,
                error=str(e),
            )

    logger.info(
        "Batch document upload completed",
        total=len(tasks),
        successful=successful,
        failed=failed,
        total_size_mb=total_size // (1024 * 1024),
    )

    return APIResponse(
        status="success" if failed == 0 else "partial",
        topic="task.document.ingest",
        metadata={
            "successful": successful,
            "failed": failed,
            "total_size_mb": total_size // (1024 * 1024),
            "errors": errors[:5],  # Limit error list
        },
    )
