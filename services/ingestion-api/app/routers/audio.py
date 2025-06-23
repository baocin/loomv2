"""WebSocket endpoints for audio data streaming."""

import json

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import JSONResponse

from ..auth import verify_api_key
from ..kafka_producer import kafka_producer
from ..models import AudioChunk, WebSocketMessage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/audio", tags=["audio"])


class ConnectionManager:
    """Manager for WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, device_id: str) -> None:
        """Accept a WebSocket connection."""
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info("WebSocket connected", device_id=device_id)

    def disconnect(self, device_id: str) -> None:
        """Remove a WebSocket connection."""
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info("WebSocket disconnected", device_id=device_id)

    async def send_message(self, device_id: str, message: dict) -> None:
        """Send a message to a specific connection."""
        if device_id in self.active_connections:
            websocket = self.active_connections[device_id]
            await websocket.send_json(message)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


# Global connection manager
connection_manager = ConnectionManager()


@router.websocket("/stream/{device_id}")
async def audio_stream_websocket(websocket: WebSocket, device_id: str) -> None:
    """WebSocket endpoint for streaming audio chunks.

    Args:
    ----
        websocket: WebSocket connection
        device_id: Unique device identifier

    """
    await connection_manager.connect(websocket, device_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                # Parse the incoming message
                message_data = json.loads(data)
                ws_message = WebSocketMessage(**message_data)

                if ws_message.message_type == "audio_chunk":
                    # Create AudioChunk from the data
                    audio_data = ws_message.data.copy()
                    audio_data["device_id"] = device_id

                    # Convert base64 chunk_data back to bytes if needed
                    if "chunk_data" in audio_data and isinstance(
                        audio_data["chunk_data"],
                        str,
                    ):
                        import base64

                        audio_data["chunk_data"] = base64.b64decode(
                            audio_data["chunk_data"],
                        )

                    audio_chunk = AudioChunk(**audio_data)

                    # Send to Kafka
                    await kafka_producer.send_audio_chunk(audio_chunk)

                    # Send acknowledgment back to client
                    await connection_manager.send_message(
                        device_id,
                        {
                            "type": "ack",
                            "message_id": audio_chunk.message_id,
                            "status": "success",
                            "topic": "device.audio.raw",
                        },
                    )

                    logger.debug(
                        "Audio chunk processed",
                        device_id=device_id,
                        message_id=audio_chunk.message_id,
                        duration_ms=audio_chunk.duration_ms,
                        sample_rate=audio_chunk.sample_rate,
                    )

                elif ws_message.message_type == "ping":
                    # Handle ping/keepalive
                    await connection_manager.send_message(
                        device_id,
                        {
                            "type": "pong",
                            "timestamp": ws_message.data.get("timestamp"),
                        },
                    )

                else:
                    # Unknown message type
                    await connection_manager.send_message(
                        device_id,
                        {
                            "type": "error",
                            "message": f"Unknown message type: {ws_message.message_type}",
                        },
                    )

            except json.JSONDecodeError as e:
                logger.error(
                    "Invalid JSON received",
                    device_id=device_id,
                    error=str(e),
                )
                await connection_manager.send_message(
                    device_id,
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                    },
                )

            except Exception as e:
                logger.error(
                    "Error processing audio message",
                    device_id=device_id,
                    error=str(e),
                )
                await connection_manager.send_message(
                    device_id,
                    {
                        "type": "error",
                        "message": "Failed to process audio data",
                    },
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", device_id=device_id)
    except Exception as e:
        logger.error(
            "WebSocket error",
            device_id=device_id,
            error=str(e),
        )
    finally:
        connection_manager.disconnect(device_id)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    audio_chunk: AudioChunk,
    api_key: str = Depends(verify_api_key),
) -> JSONResponse:
    """Upload a single audio chunk via REST.

    Args:
    ----
        audio_chunk: Audio chunk data

    Returns:
    -------
        Success response with message ID

    """
    try:
        await kafka_producer.send_audio_chunk(audio_chunk)

        logger.info(
            "Audio chunk uploaded",
            device_id=audio_chunk.device_id,
            message_id=audio_chunk.message_id,
            duration_ms=audio_chunk.duration_ms,
            sample_rate=audio_chunk.sample_rate,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "message_id": audio_chunk.message_id,
                "topic": "device.audio.raw",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to upload audio chunk",
            device_id=audio_chunk.device_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload audio chunk",
        ) from e


@router.get("/connections", status_code=status.HTTP_200_OK)
async def get_connection_status(api_key: str = Depends(verify_api_key)) -> JSONResponse:
    """Get the current WebSocket connection status.

    Returns
    -------
        Connection status information

    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "active_connections": connection_manager.get_connection_count(),
            "connected_devices": list(connection_manager.active_connections.keys()),
        },
    )
