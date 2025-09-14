"""
Debug and testing endpoints for the 7taps Analytics API.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
import os
from datetime import datetime

router = APIRouter()

@router.get("/status")
async def debug_status() -> Dict[str, Any]:
    """Get debug status information."""
    return {
        "status": "debug_endpoint_active",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }

@router.get("/env")
async def debug_environment() -> Dict[str, Any]:
    """Get environment variables (filtered for security)."""
    safe_vars = {}
    for key, value in os.environ.items():
        # Only include non-sensitive variables
        if not any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
            safe_vars[key] = value
    return safe_vars

@router.get("/health")
async def debug_health() -> Dict[str, Any]:
    """Debug health check."""
    return {
        "status": "healthy",
        "service": "debug",
        "timestamp": datetime.utcnow().isoformat()
    }

