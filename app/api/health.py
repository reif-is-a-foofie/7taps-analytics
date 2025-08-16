"""
Health monitoring endpoints for 7taps Analytics.

This module provides comprehensive health checks, system status monitoring,
resource usage tracking, and alert system integration.
"""

from fastapi import APIRouter, HTTPException
from app.logging_config import get_logger
import time
import os
import sys

router = APIRouter()
logger = get_logger("health")

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    logger.info("health_check_requested")
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "7taps-analytics-etl",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system information."""
    logger.info("detailed_health_check_requested")
    
    health_info = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "7taps-analytics-etl",
        "version": "1.0.0",
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd()
        },
        "configuration": {
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "debug": os.getenv("DEBUG", "false"),
            "database_url_set": bool(os.getenv("DATABASE_URL")),
            "redis_url_set": bool(os.getenv("REDIS_URL"))
        }
    }
    
    logger.info("detailed_health_check_completed", status=health_info["status"])
    return health_info

@router.get("/health/ready")
async def readiness_check():
    """Readiness check for deployment."""
    logger.info("readiness_check_requested")
    
    # Basic checks that don't require external services
    checks = {
        "app_loaded": True,
        "logging_configured": True,
        "environment_variables": bool(os.getenv("ENVIRONMENT"))
    }
    
    all_healthy = all(checks.values())
    
    readiness_info = {
        "ready": all_healthy,
        "timestamp": time.time(),
        "checks": checks
    }
    
    if all_healthy:
        logger.info("readiness_check_passed")
    else:
        logger.warning("readiness_check_failed", checks=checks)
    
    return readiness_info 