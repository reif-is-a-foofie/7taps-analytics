"""
Learning Locker Admin Dashboard UI.

This module provides the admin interface for Learning Locker sync management,
status monitoring, and error reporting.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List
import httpx
import json
from datetime import datetime
import os

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("learninglocker_admin")
templates = Jinja2Templates(directory="templates")

class LearningLockerAdmin:
    """Learning Locker admin interface."""
    
    def __init__(self):
        self.base_url = os.getenv("LEARNINGLOCKER_URL", "https://seventaps-analytics-5135b3a0701a.herokuapp.com/learninglocker")
        self.api_base = "https://seventaps-analytics-5135b3a0701a.herokuapp.com/api"
        
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get Learning Locker sync status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/sync-status")
                return response.json()
        except Exception as e:
            logger.error("Failed to get sync status", error=e)
            return {"error": str(e)}
    
    async def trigger_sync(self) -> Dict[str, Any]:
        """Trigger manual sync to Learning Locker."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.api_base}/sync-learninglocker")
                return response.json()
        except Exception as e:
            logger.error("Failed to trigger sync", error=e)
            return {"error": str(e)}
    
    async def get_learninglocker_info(self) -> Dict[str, Any]:
        """Get Learning Locker connection information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/learninglocker-info")
                return response.json()
        except Exception as e:
            logger.error("Failed to get Learning Locker info", error=e)
            return {"error": str(e)}
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/health/detailed")
                return response.json()
        except Exception as e:
            logger.error("Failed to get system health", error=e)
            return {"error": str(e)}

# Global admin instance
admin = LearningLockerAdmin()

@router.get("/learninglocker-admin", response_class=HTMLResponse)
async def learninglocker_admin_dashboard(request: Request):
    """Learning Locker admin dashboard."""
    try:
        # Get all status information
        sync_status = await admin.get_sync_status()
        ll_info = await admin.get_learninglocker_info()
        system_health = await admin.get_system_health()
        
        context = {
            "request": request,
            "sync_status": sync_status,
            "learninglocker_info": ll_info,
            "system_health": system_health,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return templates.TemplateResponse("learninglocker_admin.html", context)
        
    except Exception as e:
        logger.error("Failed to render admin dashboard", error=e)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.post("/api/learninglocker/trigger-sync")
async def trigger_manual_sync():
    """Trigger manual sync to Learning Locker."""
    try:
        result = await admin.trigger_sync()
        logger.info("Manual sync triggered", result=result)
        return result
    except Exception as e:
        logger.error("Failed to trigger manual sync", error=e)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/api/learninglocker/status")
async def get_admin_status():
    """Get comprehensive admin status."""
    try:
        sync_status = await admin.get_sync_status()
        ll_info = await admin.get_learninglocker_info()
        system_health = await admin.get_system_health()
        
        return {
            "sync_status": sync_status,
            "learninglocker_info": ll_info,
            "system_health": system_health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to get admin status", error=e)
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/api/learninglocker/logs")
async def get_sync_logs():
    """Get recent sync logs."""
    try:
        # This would typically fetch from a log database
        # For now, return mock logs
        logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "info",
                "message": "Sync completed successfully",
                "statements_processed": 25,
                "duration_ms": 1200
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "warning",
                "message": "Some statements failed to sync",
                "statements_processed": 20,
                "failed_count": 5,
                "duration_ms": 1500
            }
        ]
        
        return {"logs": logs}
    except Exception as e:
        logger.error("Failed to get sync logs", error=e)
        raise HTTPException(status_code=500, detail=f"Log retrieval failed: {str(e)}")

@router.get("/api/learninglocker/metrics")
async def get_sync_metrics():
    """Get sync performance metrics."""
    try:
        sync_status = await admin.get_sync_status()
        
        # Calculate metrics from sync status
        metrics = {
            "total_synced": sync_status.get("learninglocker_sync", {}).get("total_synced", 0),
            "last_sync_time": sync_status.get("learninglocker_sync", {}).get("last_sync_time"),
            "sync_success_rate": 95.5,  # Mock success rate
            "average_sync_duration_ms": 1250,
            "statements_per_minute": 45,
            "error_rate": 4.5
        }
        
        return metrics
    except Exception as e:
        logger.error("Failed to get sync metrics", error=e)
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}") 