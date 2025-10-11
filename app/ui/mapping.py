"""
Manual mapping UI for activities and users.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from typing import Dict, Any
import httpx

from app.logging_config import get_logger

logger = get_logger("mapping_ui")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/mapping", response_class=HTMLResponse)
async def mapping_dashboard(request: Request):
    """Manual mapping interface for unmapped activities and users."""
    try:
        # Fetch unmapped activities and users from debug endpoints
        async with httpx.AsyncClient() as client:
            # Get base URL from request
            base_url = str(request.base_url).rstrip('/')
            
            # Fetch unmapped activities
            activities_response = await client.get(f"{base_url}/api/debug/unmapped-activities")
            activities_data = activities_response.json() if activities_response.status_code == 200 else {
                "unmapped_activities": [],
                "mapped_activities": [],
                "summary": {"total_activities": 0, "mapped": 0, "unmapped": 0}
            }
            
            # Fetch unmapped users
            users_response = await client.get(f"{base_url}/api/debug/unmapped-users")
            users_data = users_response.json() if users_response.status_code == 200 else {
                "users": [],
                "summary": {"total_users": 0}
            }
        
        context = {
            "request": request,
            "activities_data": activities_data,
            "users_data": users_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_page": "mapping",
            "title": "Manual Mapping"
        }
        
        return templates.TemplateResponse("mapping_dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Error loading mapping dashboard: {e}")
        # Return empty data on error
        context = {
            "request": request,
            "activities_data": {
                "unmapped_activities": [],
                "mapped_activities": [],
                "summary": {"total_activities": 0, "mapped": 0, "unmapped": 0}
            },
            "users_data": {
                "users": [],
                "summary": {"total_users": 0}
            },
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_page": "mapping",
            "title": "Manual Mapping"
        }
        return templates.TemplateResponse("mapping_dashboard.html", context)

