"""Image and photo ingestion endpoints."""

import base64

import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import APIResponse, ImageData

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/images", tags=["images"])


@router.post("/upload", response_model=APIResponse)
async def upload_image(
    image: ImageData,
    api_key: str = Depends(verify_api_key),
) -> APIResponse:
    """Upload an image or photo.

    Args:
    ----
        image: Image data including base64 encoded image and metadata

    Returns:
    -------
        APIResponse with status and message ID

    """
    try:
        # Validate base64 encoding
        try:
            base64.b64decode(image.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        # Send to Kafka topic
        await kafka_producer.send_message(
            topic="device.image.camera.raw",
            message=image,
        )

        logger.info(
            "Image uploaded successfully",
            device_id=image.device_id,
            message_id=image.message_id,
            format=image.format,
            dimensions=f"{image.width}x{image.height}",
            camera_type=image.camera_type,
            file_size=image.file_size,
        )

        return APIResponse(
            status="success",
            message_id=image.message_id,
            topic="device.image.camera.raw",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to upload image",
            device_id=image.device_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to upload image")


@router.post("/screenshot", response_model=APIResponse)
async def upload_screenshot(image: ImageData) -> APIResponse:
    """Upload a screenshot.

    Args:
    ----
        image: Screenshot image data

    Returns:
    -------
        APIResponse with status and message ID

    """
    try:
        # Validate base64 encoding
        try:
            base64.b64decode(image.image_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        # Force camera_type to screen for screenshots
        image.camera_type = "screen"

        # Send to Kafka topic for screen recordings
        await kafka_producer.send_message(
            topic="device.video.screen.raw",
            message=image,
        )

        logger.info(
            "Screenshot uploaded successfully",
            device_id=image.device_id,
            message_id=image.message_id,
            format=image.format,
            dimensions=f"{image.width}x{image.height}",
            file_size=image.file_size,
        )

        return APIResponse(
            status="success",
            message_id=image.message_id,
            topic="device.video.screen.raw",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to upload screenshot",
            device_id=image.device_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Failed to upload screenshot")


@router.post("/batch", response_model=APIResponse)
async def upload_images_batch(images: list[ImageData]) -> APIResponse:
    """Upload multiple images in a single request.

    Args:
    ----
        images: List of image data objects

    Returns:
    -------
        APIResponse with batch processing status

    """
    if len(images) > 50:  # Lower limit for images due to size
        raise HTTPException(
            status_code=400,
            detail="Batch size too large (max 50 images)",
        )

    successful = 0
    failed = 0
    errors = []

    for image in images:
        try:
            # Validate base64 encoding
            base64.b64decode(image.image_data)

            # Choose topic based on camera type
            topic = (
                "device.video.screen.raw"
                if image.camera_type == "screen"
                else "device.image.camera.raw"
            )

            await kafka_producer.send_message(
                topic=topic,
                message=image,
            )
            successful += 1

        except Exception as e:
            failed += 1
            errors.append(f"Image {image.message_id}: {e!s}")
            logger.error(
                "Failed to upload image in batch",
                device_id=image.device_id,
                message_id=image.message_id,
                error=str(e),
            )

    logger.info(
        "Batch image upload completed",
        total=len(images),
        successful=successful,
        failed=failed,
    )

    return APIResponse(
        status="success" if failed == 0 else "partial",
        topic="device.image.camera.raw",
    )
