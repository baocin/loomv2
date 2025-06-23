"""Notes and text content ingestion endpoints."""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import APIResponse, NoteData

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/upload", response_model=APIResponse)
async def upload_note(
    note: NoteData,
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Upload a text note or memo.

    Args:
    ----
        note: Note data including content, title, and metadata

    Returns:
    -------
        APIResponse with status and message ID

    """
    try:
        # Send to Kafka topic
        await kafka_producer.send_message(
            topic="device.text.notes.raw",
            message=note,
        )

        logger.info(
            "Note uploaded successfully",
            device_id=note.device_id,
            message_id=note.message_id,
            word_count=note.word_count,
            note_type=note.note_type,
        )

        return APIResponse(
            status="success",
            message_id=note.message_id,
            topic="device.text.notes.raw",
        )

    except Exception as e:
        logger.error(
            "Failed to upload note",
            device_id=note.device_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to upload note")


@router.post("/batch", response_model=APIResponse)
async def upload_notes_batch(notes: list[NoteData]) -> APIResponse:
    """Upload multiple notes in a single request.

    Args:
    ----
        notes: List of note data objects

    Returns:
    -------
        APIResponse with batch processing status

    """
    if len(notes) > 100:  # Configurable limit
        raise HTTPException(
            status_code=400,
            detail="Batch size too large (max 100 notes)",
        )

    successful = 0
    failed = 0
    errors = []

    for note in notes:
        try:
            await kafka_producer.send_message(
                topic="device.text.notes.raw",
                message=note,
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(f"Note {note.message_id}: {e!s}")
            logger.error(
                "Failed to upload note in batch",
                device_id=note.device_id,
                message_id=note.message_id,
                error=str(e),
            )

    logger.info(
        "Batch note upload completed",
        total=len(notes),
        successful=successful,
        failed=failed,
    )

    return APIResponse(
        status="success" if failed == 0 else "partial",
        topic="device.text.notes.raw",
    )


@router.post("/digital", response_model=APIResponse)
async def upload_digital_note(note: NoteData) -> APIResponse:
    """Upload a digital note, document, or markdown file.

    This endpoint is for general digital content like:
    - Markdown documents
    - Text files
    - Research notes
    - External documents

    Args:
    ----
        note: Note data including content, title, and metadata

    Returns:
    -------
        APIResponse with status and message ID

    """
    try:
        # Send to digital notes topic
        await kafka_producer.send_message(
            topic="digital.notes.raw",
            message=note,
        )

        logger.info(
            "Digital note uploaded successfully",
            device_id=note.device_id,
            message_id=note.message_id,
            word_count=note.word_count,
            note_type=note.note_type,
        )

        return APIResponse(
            status="success",
            message_id=note.message_id,
            topic="digital.notes.raw",
        )

    except Exception as e:
        logger.error(
            "Failed to upload digital note",
            device_id=note.device_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to upload digital note")
