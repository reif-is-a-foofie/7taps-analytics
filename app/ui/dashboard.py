"""
Analytics Dashboard UI.

This module provides the analytics dashboard with comprehensive metrics
visualization and real-time data display.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, List
import httpx
import json
from datetime import datetime
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
            # Use localhost for development
            self.api_base = "http://localhost:8000/api"

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get comprehensive dashboard metrics."""
        try:
            async with httpx.AsyncClient() as client:
                # Get health metrics
                health_response = await client.get(f"{self.api_base}/health/detailed")
                health_data = health_response.json() if health_response.status_code == 200 else {"status": "unknown"}

                # Get database metrics (mock data for now)
                db_metrics = {
                    "total_users": 150,
                    "total_activities": 2500,
                    "total_responses": 1800,
                    "total_lessons": 50,  # Changed from total_questions to total_lessons
                    "completion_rate": 78.5,
                    "active_users_today": 45,
                    "avg_session_duration": 12.3
                }

                # Get learning analytics
                analytics_data = {
                    "lesson_completion": [
                        {"lesson": "Lesson 1", "completed": 85, "total": 120},
                        {"lesson": "Lesson 2", "completed": 92, "total": 118},
                        {"lesson": "Lesson 3", "completed": 78, "total": 125}
                    ],
                    "activity_trends": [
                        {"date": "2024-01-01", "activities": 45, "users": 12},
                        {"date": "2024-01-02", "activities": 67, "users": 18},
                        {"date": "2024-01-03", "activities": 89, "users": 23}
                    ],
                    "response_distribution": [
                        {"type": "Multiple Choice", "count": 450},
                        {"type": "Text Response", "count": 380},
                        {"type": "Rating", "count": 290}
                    ]
                }

                return {
                    "health": health_data,
                    "metrics": db_metrics,
                    "analytics": analytics_data,
                    "timestamp": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error("Failed to get dashboard metrics", error=e)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Global dashboard manager
dashboard_manager = DashboardManager()

@router.get("/dashboard", response_class=HTMLResponse)
async def analytics_dashboard(request: Request):
    """Serve the analytics dashboard."""
    try:
        # Get dashboard data
        dashboard_data = await dashboard_manager.get_dashboard_metrics()

        context = {
            "request": request,
            "dashboard_data": json.dumps(dashboard_data),
            "timestamp": datetime.utcnow().isoformat(),
            "active_page": "dashboard",
            "title": "Analytics Dashboard"
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
        "timestamp": datetime.utcnow().isoformat()
    }
