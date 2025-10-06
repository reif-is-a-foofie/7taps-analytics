"""
Analytics Dashboard UI.

This module provides the analytics dashboard with comprehensive metrics
visualization and real-time data display.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any
import httpx
from datetime import datetime, timezone
import os

from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("dashboard")
templates = Jinja2Templates(directory="templates")

class DashboardManager:
    """Analytics dashboard manager."""

    def __init__(self):
        api_base_url = os.getenv("API_BASE_URL", "")
        if api_base_url:
            self.api_base = api_base_url.rstrip("/") + "/api"
        else:
            # Use proper base URL for environment
            if os.getenv("ENVIRONMENT") == "development":
                self.api_base = "http://localhost:8000/api"
            else:
                self.api_base = "https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/api"

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics with real data."""
        try:
            async with httpx.AsyncClient() as client:
                health_data: Dict[str, Any] = {"status": "unknown"}
                alerts_data: Dict[str, Any] = {}

                health_response = await client.get(f"{self.api_base}/health/detailed")
                if health_response.status_code == 200:
                    health_data = health_response.json()

                alerts_response = await client.get(
                    f"{self.api_base}/xapi/alerts/trigger-words",
                    params={"limit": 25},
                )
                if alerts_response.status_code == 200:
                    alerts_data = alerts_response.json()

                return {
                    "health": health_data,
                    "metrics": {},
                    "trigger_word_alerts": alerts_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            logger.error("Failed to get dashboard metrics", error=e)
            return {
                "health": {"status": "error"},
                "metrics": {},
                "trigger_word_alerts": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

# Global dashboard manager
dashboard_manager = DashboardManager()

@router.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """Serve the analytics dashboard."""
    try:
        dashboard_data = await dashboard_manager.get_dashboard_metrics()

        context = {
            "request": request,
            "dashboard_data": dashboard_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_page": "dashboard",
            "title": "Analytics Dashboard",
        }

        return templates.TemplateResponse("dashboard.html", context)

    except Exception as e:
        logger.error("Failed to render dashboard", error=e)
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@router.get("/api/dashboard/metrics")
async def get_dashboard_metrics():
    """Get dashboard metrics API endpoint."""
    try:
        return await dashboard_manager.get_dashboard_metrics()
    except Exception as e:
        logger.error("Failed to get dashboard metrics", error=e)
        raise HTTPException(status_code=500, detail=f"Metrics error: {str(e)}")

@router.get("/api/dashboard/health")
async def dashboard_health():
    """Dashboard health check."""
    return {
        "status": "healthy",
        "service": "analytics-dashboard",
        "endpoints": [
            "/ui/dashboard",
            "/api/dashboard/metrics"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
