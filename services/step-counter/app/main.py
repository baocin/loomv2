"""Main application with health endpoints."""

import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Response
import uvicorn

from .config import settings
from .consumer import StepCounterConsumer

# Global consumer instance
consumer: Optional[StepCounterConsumer] = None
consumer_thread: Optional[threading.Thread] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global consumer, consumer_thread
    
    # Startup
    consumer = StepCounterConsumer()
    consumer_thread = threading.Thread(target=consumer.start, daemon=True)
    consumer_thread.start()
    
    yield
    
    # Shutdown
    if consumer:
        consumer.cleanup()


app = FastAPI(
    title="Step Counter",
    description="Counts steps from accelerometer data",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/healthz")
async def liveness():
    """Liveness probe endpoint."""
    return {"status": "alive"}


@app.get("/readyz")
async def readiness():
    """Readiness probe endpoint."""
    global consumer
    
    if consumer and consumer.running:
        return {"status": "ready"}
    else:
        return Response(
            content='{"status": "not ready"}',
            status_code=503,
            media_type="application/json"
        )


@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint."""
    global consumer
    
    metrics_data = {
        "devices_tracked": len(consumer.detectors) if consumer else 0,
        "consumer_running": consumer.running if consumer else False,
        "total_steps": sum(d.total_steps for d in consumer.detectors.values()) if consumer else 0,
        "daily_steps": sum(d.daily_steps for d in consumer.detectors.values()) if consumer else 0
    }
    
    return metrics_data


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )