#!/usr/bin/env python3
"""Kafka Test Producer - Generate and send example messages to any Kafka topic."""

import json
import os
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
from kafka.errors import KafkaError
from pydantic import BaseModel, Field

from .example_payloads import ExamplePayloads


# Custom JSON encoder to handle Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def serialize_json(obj):
    """Serialize object to JSON, handling Decimal types."""
    return json.dumps(obj, cls=DecimalEncoder)


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Set up logger
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Kafka Test Producer",
    description="Generate and send example messages to any Kafka topic in the Loom v2 system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8082",
    ],  # Pipeline monitor frontend and API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

# Initialize Kafka producer
producer = None


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    topic: str = Field(..., description="Kafka topic to send message to")
    message: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom message payload (if not provided, example will be used)",
    )
    key: Optional[str] = Field(None, description="Message key for partitioning")
    count: int = Field(1, ge=1, le=100, description="Number of messages to send")


class BulkSendRequest(BaseModel):
    """Request model for sending messages to multiple topics."""

    topics: List[str] = Field(..., description="List of topics to send messages to")
    count_per_topic: int = Field(
        1, ge=1, le=50, description="Number of messages per topic"
    )


class SendMessageResponse(BaseModel):
    """Response model for message sending."""

    success: bool
    topic: str
    count: int
    timestamp: str
    details: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize Kafka producer on startup."""
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        logger.info(
            "Kafka producer initialized", bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
        )
    except Exception as e:
        logger.error("Failed to initialize Kafka producer", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up Kafka producer on shutdown."""
    global producer
    if producer:
        producer.close()
        logger.info("Kafka producer closed")


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Kafka Test Producer",
        "version": "1.0.0",
        "description": "Generate and send example messages to Kafka topics",
        "endpoints": {
            "GET /topics": "List all available topics with example payloads",
            "GET /topics/{topic}": "Get example payload for specific topic",
            "POST /send": "Send message(s) to a topic",
            "POST /send/bulk": "Send messages to multiple topics",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if producer is initialized
        if not producer:
            raise HTTPException(
                status_code=503, detail="Kafka producer not initialized"
            )

        # Try to get metadata to verify connection
        metadata = producer._metadata
        if metadata:
            return {
                "status": "healthy",
                "kafka_connected": True,
                "brokers": len(metadata.brokers()),
            }
        else:
            return {
                "status": "degraded",
                "kafka_connected": False,
                "message": "No metadata available",
            }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.get("/topics")
async def list_topics():
    """List all available topics with descriptions."""
    topics = ExamplePayloads.get_topic_list()

    # Group topics by category
    categorized = {
        "Device Data": [t for t in topics if t.startswith("device.")],
        "External Sources": [t for t in topics if t.startswith("external.")],
        "Media Processing": [t for t in topics if t.startswith("media.")],
        "Analysis Results": [t for t in topics if t.startswith("analysis.")],
        "Tasks": [t for t in topics if t.startswith("task.")],
    }

    return {
        "total_topics": len(topics),
        "categories": categorized,
        "all_topics": sorted(topics),
    }


@app.get("/topics/{topic}")
async def get_topic_example(topic: str):
    """Get example payload for a specific topic."""
    all_examples = ExamplePayloads.get_all_topics()

    if topic not in all_examples:
        available_topics = sorted(all_examples.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Topic '{topic}' not found. Available topics: {', '.join(available_topics)}",
        )

    # Get the example payload
    example_payload = all_examples[topic]

    # Calculate size using custom encoder
    try:
        payload_json = serialize_json(example_payload)
        payload_size = len(payload_json)
    except Exception as e:
        logger.warning(f"Could not serialize example payload for topic {topic}: {e}")
        payload_size = 0

    response_data = {
        "topic": topic,
        "example_payload": example_payload,
        "payload_size_bytes": payload_size,
    }

    # Return JSONResponse with custom encoder
    return JSONResponse(content=json.loads(serialize_json(response_data)))


@app.post("/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send message(s) to a Kafka topic."""
    if not producer:
        raise HTTPException(status_code=503, detail="Kafka producer not initialized")

    try:
        sent_count = 0

        for i in range(request.count):
            # Use custom message or generate example
            if request.message:
                message = request.message
            else:
                # Get example payload for the topic
                all_examples = ExamplePayloads.get_all_topics()
                if request.topic in all_examples:
                    # Generate fresh example for each message
                    topic_method = request.topic.replace(".", "_")
                    if hasattr(ExamplePayloads, topic_method):
                        message = getattr(ExamplePayloads, topic_method)()
                    else:
                        message = all_examples[request.topic]
                else:
                    # Generic message for unknown topics
                    message = {
                        "schema_version": "v1",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "test": True,
                        "message": f"Test message {i+1} for topic {request.topic}",
                    }

            # Send to Kafka
            future = producer.send(request.topic, value=message, key=request.key)

            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            sent_count += 1

            logger.info(
                "Message sent",
                topic=request.topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                message_num=i + 1,
                total_count=request.count,
            )

        return SendMessageResponse(
            success=True,
            topic=request.topic,
            count=sent_count,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details=f"Successfully sent {sent_count} message(s)",
        )

    except KafkaError as e:
        logger.error("Kafka error", error=str(e), topic=request.topic)
        raise HTTPException(status_code=500, detail=f"Kafka error: {str(e)}")
    except Exception as e:
        logger.error("Error sending message", error=str(e), topic=request.topic)
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")


@app.post("/send/bulk")
async def send_bulk_messages(request: BulkSendRequest):
    """Send messages to multiple topics."""
    if not producer:
        raise HTTPException(status_code=503, detail="Kafka producer not initialized")

    results = []
    total_sent = 0

    for topic in request.topics:
        try:
            # Send messages to this topic
            send_request = SendMessageRequest(
                topic=topic, count=request.count_per_topic
            )
            result = await send_message(send_request)
            results.append(result.dict())
            total_sent += result.count

        except HTTPException as e:
            results.append(
                {
                    "success": False,
                    "topic": topic,
                    "count": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "details": e.detail,
                }
            )
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "topic": topic,
                    "count": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "details": str(e),
                }
            )

    return {
        "total_topics": len(request.topics),
        "total_messages_sent": total_sent,
        "results": results,
    }


@app.get("/examples")
async def get_all_examples():
    """Get example payloads for all topics."""
    all_examples = ExamplePayloads.get_all_topics()
    return JSONResponse(content=json.loads(serialize_json(all_examples)))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
