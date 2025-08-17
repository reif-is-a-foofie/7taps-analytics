"""
Production Dashboard UI for real-time monitoring
Provides web interface for system metrics, alerts, and performance monitoring
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/production-dashboard", response_class=HTMLResponse)
async def production_dashboard(request: Request):
    """Main production dashboard page"""
    try:
        return templates.TemplateResponse(
            "production_dashboard.html",
            {
                "request": request,
                "title": "7taps Analytics - Production Dashboard",
                "timestamp": datetime.now().isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Dashboard rendering failed: {e}")
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>Dashboard Error</title></head>
                <body>
                    <h1>Dashboard Error</h1>
                    <p>Failed to load dashboard: {str(e)}</p>
                    <a href="/api/monitoring/health">Health Check</a>
                </body>
            </html>
            """,
            status_code=500,
        )


@router.get("/dashboard/metrics")
async def get_dashboard_metrics():
    """Get metrics for dashboard display"""
    try:
        # This would typically call the monitoring API
        # For now, return a placeholder structure
        return {
            "system_health": {
                "status": "healthy",
                "cpu_percent": 25.5,
                "memory_percent": 45.2,
                "disk_percent": 30.1,
                "database_connected": True,
                "redis_connected": True,
            },
            "data_metrics": {
                "statements_flat_count": 261,
                "statements_normalized_count": 1,
                "actors_count": 15,
                "activities_count": 25,
                "verbs_count": 8,
                "processing_rate": 2.5,
                "error_rate": 0.1,
            },
            "alerts": {"total": 0, "critical": 0, "warning": 0, "active": []},
            "performance": {
                "avg_cpu_percent": 22.3,
                "avg_memory_percent": 42.1,
                "avg_processing_rate": 2.8,
                "normalization_ratio": 0.38,
            },
        }
    except Exception as e:
        logger.error(f"Dashboard metrics retrieval failed: {e}")
        return {"error": str(e)}


@router.get("/dashboard/alerts")
async def get_dashboard_alerts():
    """Get alerts for dashboard display"""
    try:
        # This would typically call the monitoring API
        return {
            "alerts": [],
            "summary": {"total": 0, "critical": 0, "warning": 0, "error": 0, "info": 0},
        }
    except Exception as e:
        logger.error(f"Dashboard alerts retrieval failed: {e}")
        return {"error": str(e)}


@router.get("/dashboard/analytics")
async def get_dashboard_analytics():
    """Get analytics insights for dashboard display"""
    try:
        # This would typically call the monitoring API
        return {
            "top_activities": [
                {"activity": "Card 6 (Form)", "count": 15},
                {"activity": "Card 8 (Poll)", "count": 12},
                {"activity": "Card 3 (Quiz)", "count": 8},
            ],
            "top_actors": [
                {"actor": "Audrey Todd", "count": 25},
                {"actor": "John Smith", "count": 18},
                {"actor": "Jane Doe", "count": 15},
            ],
            "processing_efficiency": {
                "total_statements": 261,
                "successful_statements": 250,
                "success_rate": 95.8,
            },
            "cohort_analytics": [
                {"cohort": "Focus Group", "member_count": 15, "active_learners": 12},
                {"cohort": "Sacramento State", "member_count": 8, "active_learners": 6},
            ],
        }
    except Exception as e:
        logger.error(f"Dashboard analytics retrieval failed: {e}")
        return {"error": str(e)}
