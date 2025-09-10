from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Templates setup
templates = Jinja2Templates(directory="templates")

class BigQueryDashboardConfig:
    def __init__(self):
        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize config
dashboard_config = BigQueryDashboardConfig()

@router.get("/bigquery-dashboard", response_class=HTMLResponse)
async def bigquery_dashboard_page(request: Request):
    """Serve the BigQuery analytics dashboard page."""
    return templates.TemplateResponse(
        "bigquery_dashboard.html",
        {
            "request": request,
            "api_base_url": dashboard_config.api_base_url
        }
    )

@router.get("/bigquery-dashboard/data")
async def get_dashboard_data():
    """Get comprehensive dashboard data from BigQuery analytics API."""
    try:
        async with httpx.AsyncClient() as client:
            # Get connection status
            status_response = await client.get(
                f"{dashboard_config.api_base_url}/api/analytics/bigquery/connection-status"
            )
            connection_status = status_response.json() if status_response.status_code == 200 else {"status": "unknown"}

            # Get learner activity summary
            learner_response = await client.get(
                f"{dashboard_config.api_base_url}/api/analytics/bigquery/learner-activity-summary"
            )
            learner_data = learner_response.json() if learner_response.status_code == 200 else {"success": False}

            # Get verb distribution
            verb_response = await client.get(
                f"{dashboard_config.api_base_url}/api/analytics/bigquery/verb-distribution"
            )
            verb_data = verb_response.json() if verb_response.status_code == 200 else {"success": False}

            # Get activity timeline (last 30 days)
            timeline_response = await client.get(
                f"{dashboard_config.api_base_url}/api/analytics/bigquery/activity-timeline?days=30"
            )
            timeline_data = timeline_response.json() if timeline_response.status_code == 200 else {"success": False}

            return {
                "connection_status": connection_status,
                "learner_summary": learner_data,
                "verb_distribution": verb_data,
                "activity_timeline": timeline_data,
                "dashboard_ready": connection_status.get("status") == "connected"
            }

    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        return {
            "connection_status": {"status": "error", "error": str(e)},
            "learner_summary": {"success": False, "error": str(e)},
            "verb_distribution": {"success": False, "error": str(e)},
            "activity_timeline": {"success": False, "error": str(e)},
            "dashboard_ready": False
        }

@router.post("/bigquery-dashboard/query")
async def execute_dashboard_query(request: Request):
    """Execute a custom query from the dashboard."""
    try:
        data = await request.json()
        query = data.get("query", "")
        chart_type = data.get("chart_type", "table")

        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{dashboard_config.api_base_url}/api/analytics/bigquery/query",
                params={
                    "query": query,
                    "chart_type": chart_type
                }
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Query execution failed")

            return response.json()

    except Exception as e:
        logger.error(f"Error executing dashboard query: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@router.get("/bigquery-dashboard/health")
async def dashboard_health():
    """Health check for BigQuery dashboard."""
    return {
        "status": "healthy",
        "service": "bigquery-dashboard",
        "endpoints": [
            "/ui/bigquery-dashboard",
            "/ui/bigquery-dashboard/data",
            "/ui/bigquery-dashboard/query"
        ],
        "api_base_url": dashboard_config.api_base_url
    }
