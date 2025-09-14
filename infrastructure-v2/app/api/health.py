"""
Health check and system status endpoints.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import structlog
import psutil
import time
from datetime import datetime

from config.settings import settings
from config.gcp_config import gcp_config

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": settings.environment
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with system metrics."""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # GCP connection status
        gcp_status = gcp_config.validate_connection()
        
        # Overall health status
        is_healthy = (
            cpu_percent < 90 and
            memory.percent < 90 and
            disk.percent < 90 and
            gcp_status["credentials"] == "valid"
        )
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "environment": settings.environment,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "uptime_seconds": time.time() - psutil.boot_time()
            },
            "gcp": gcp_status,
            "checks": {
                "cpu": "healthy" if cpu_percent < 90 else "warning",
                "memory": "healthy" if memory.percent < 90 else "warning",
                "disk": "healthy" if disk.percent < 90 else "warning",
                "gcp": "healthy" if gcp_status["credentials"] == "valid" else "error"
            }
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes/load balancer."""
    try:
        # Check critical dependencies
        gcp_status = gcp_config.validate_connection()
        
        is_ready = (
            gcp_status["credentials"] == "valid" and
            all(status == "connected" for status in gcp_status["services"].values())
        )
        
        return {
            "ready": is_ready,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": gcp_status["services"]
        }
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "ready": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/health/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes."""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - psutil.boot_time()
    }

