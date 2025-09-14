"""
Monitoring API endpoints for production monitoring system
Provides health checks, metrics, alerts, and performance monitoring
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
import os
import logging
from datetime import datetime, timedelta

from config.settings import settings
from config.gcp_config import gcp_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """System health check endpoint"""
    try:
        # Test GCP connections
        gcp_status = gcp_config.validate_connection()
        
        # Basic system health
        is_healthy = (
            gcp_status["credentials"] == "valid" and
            all(status == "connected" for status in gcp_status["services"].values())
        )
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "environment": settings.environment,
            "gcp_status": gcp_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@router.get("/metrics")
async def get_metrics():
    """Get comprehensive system and data metrics"""
    try:
        gcp_status = gcp_config.validate_connection()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.environment,
            "gcp_status": gcp_status,
            "config": {
                "project_id": gcp_config.project_id,
                "bigquery_dataset": settings.bigquery_dataset,
                "pubsub_topic": settings.pubsub_topic,
                "storage_bucket": settings.storage_bucket
            }
        }
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

@router.get("/status")
async def get_system_status():
    """Get comprehensive system status overview"""
    try:
        gcp_status = gcp_config.validate_connection()
        
        # Determine overall status
        if gcp_status["credentials"] != "valid":
            status = "critical"
        elif any("error" in str(status) for status in gcp_status["services"].values()):
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "environment": settings.environment,
            "gcp_status": gcp_status,
            "summary": {
                "credentials": gcp_status["credentials"],
                "services": gcp_status["services"],
                "project_id": gcp_config.project_id
            }
        }
    except Exception as e:
        logger.error(f"System status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"System status retrieval failed: {str(e)}")

@router.get("/config")
async def get_monitoring_config():
    """Get monitoring configuration and thresholds"""
    try:
        return {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.environment,
            "gcp_config": {
                "project_id": gcp_config.project_id,
                "bigquery_dataset": settings.bigquery_dataset,
                "pubsub_topic": settings.pubsub_topic,
                "storage_bucket": settings.storage_bucket
            },
            "app_config": {
                "app_name": settings.app_name,
                "debug": settings.debug,
                "log_level": settings.log_level
            }
        }
    except Exception as e:
        logger.error(f"Monitoring config retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Monitoring config retrieval failed: {str(e)}")

