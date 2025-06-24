"""Local REST API server for monitoring and controlling the client."""

from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)


class ConfigUpdate(BaseModel):
    """Model for configuration updates."""
    audio_enabled: bool | None = None
    screen_enabled: bool | None = None
    system_enabled: bool | None = None
    location_enabled: bool | None = None
    clipboard_enabled: bool | None = None
    apps_enabled: bool | None = None
    audio_interval: int | None = None
    screen_interval: int | None = None
    system_interval: int | None = None


def create_server(client, config) -> FastAPI:
    """Create the local FastAPI server."""
    app = FastAPI(
        title="Loom macOS Client API",
        description="Local API for monitoring and controlling the Loom macOS client",
        version="0.1.0"
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "loom-macos-client"}
    
    @app.get("/status")
    async def get_status():
        """Get detailed client status."""
        try:
            status = await client.get_status()
            return status
        except Exception as e:
            logger.error("Error getting status", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/config")
    async def get_config():
        """Get current configuration."""
        return config.to_dict()
    
    @app.post("/config")
    async def update_config(update: ConfigUpdate):
        """Update configuration."""
        try:
            # Update configuration
            update_dict = update.dict(exclude_unset=True)
            config.update(**update_dict)
            
            logger.info("Configuration updated", updates=update_dict)
            return {"status": "success", "updated": update_dict}
            
        except Exception as e:
            logger.error("Error updating config", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/start")
    async def start_collection():
        """Start data collection."""
        try:
            if client.is_running:
                return {"status": "already_running"}
            
            await client.start()
            return {"status": "started"}
            
        except Exception as e:
            logger.error("Error starting collection", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/stop")
    async def stop_collection():
        """Stop data collection."""
        try:
            if not client.is_running:
                return {"status": "already_stopped"}
            
            await client.stop()
            return {"status": "stopped"}
            
        except Exception as e:
            logger.error("Error stopping collection", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/restart")
    async def restart_collection():
        """Restart data collection."""
        try:
            await client.stop()
            await client.start()
            return {"status": "restarted"}
            
        except Exception as e:
            logger.error("Error restarting collection", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/collectors")
    async def get_collectors():
        """Get information about all collectors."""
        try:
            collectors_info = {}
            for name, collector in client.collectors.items():
                collectors_info[name] = {
                    "enabled": True,
                    "interval": collector.interval,
                    "status": await collector.get_status()
                }
            return collectors_info
            
        except Exception as e:
            logger.error("Error getting collectors info", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/collectors/{collector_name}/restart")
    async def restart_collector(collector_name: str):
        """Restart a specific collector."""
        try:
            success = await client.scheduler.restart_collector(collector_name)
            if success:
                return {"status": "restarted", "collector": collector_name}
            else:
                raise HTTPException(status_code=404, detail="Collector not found")
                
        except Exception as e:
            logger.error("Error restarting collector", 
                        collector=collector_name, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/collectors/{collector_name}/pause")
    async def pause_collector(collector_name: str):
        """Pause a specific collector."""
        try:
            success = client.scheduler.pause_collector(collector_name)
            if success:
                return {"status": "paused", "collector": collector_name}
            else:
                raise HTTPException(status_code=404, detail="Collector not found")
                
        except Exception as e:
            logger.error("Error pausing collector", 
                        collector=collector_name, error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/logs")
    async def get_recent_logs():
        """Get recent log entries."""
        # This would read from log files
        # For now, return a placeholder
        return {
            "logs": [
                {"timestamp": "2024-01-01T00:00:00Z", "level": "INFO", "message": "Client started"},
                {"timestamp": "2024-01-01T00:01:00Z", "level": "INFO", "message": "Data collection active"}
            ]
        }
    
    @app.get("/metrics")
    async def get_metrics():
        """Get client metrics."""
        try:
            # This would collect various metrics about the client
            return {
                "uptime_seconds": 0,  # Would calculate actual uptime
                "collections_count": 0,  # Would track collection attempts
                "errors_count": 0,  # Would track errors
                "api_requests_count": 0,  # Would track API calls
                "last_collection": "2024-01-01T00:00:00Z"  # Would track last successful collection
            }
        except Exception as e:
            logger.error("Error getting metrics", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    
    return app