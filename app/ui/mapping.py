"""
Manual mapping UI for activities and users.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path
import httpx
import json

from app.logging_config import get_logger

logger = get_logger("mapping_ui")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class ActivityMapping(BaseModel):
    activity_url: str
    lesson_number: str
    lesson_name: str


class UserGroupMapping(BaseModel):
    actor_name: str
    group_name: str


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
        
        # Get available lessons for dropdown
        from app.config import settings
        settings._load_lesson_mapping()
        available_lessons = settings._lesson_mapping or {}
        
        context = {
            "request": request,
            "activities_data": activities_data,
            "users_data": users_data,
            "available_lessons": available_lessons,
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
            "available_lessons": {},
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_page": "mapping",
            "title": "Manual Mapping"
        }
        return templates.TemplateResponse("mapping_dashboard.html", context)


@router.post("/mapping/save-activity")
async def save_activity_mapping(mapping: ActivityMapping):
    """Save an activity to lesson mapping."""
    try:
        # Load current lesson mapping
        mapping_path = Path(__file__).parent.parent / "data" / "lesson_mapping.json"
        
        with open(mapping_path, 'r') as f:
            data = json.load(f)
        
        # Check if lesson number exists
        lesson_key = str(mapping.lesson_number)
        if lesson_key not in data.get("lessons", {}):
            raise HTTPException(status_code=400, detail=f"Lesson {lesson_key} not found in mapping")
        
        # Update the lesson URL
        data["lessons"][lesson_key]["lesson_url"] = mapping.activity_url
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Save back to file
        with open(mapping_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Reload the mapping in config
        from app.config import settings
        settings._lesson_mapping = None
        settings._lesson_url_reverse = None
        settings._load_lesson_mapping()
        
        logger.info(f"Mapped activity {mapping.activity_url} to lesson {mapping.lesson_number}")
        
        return {
            "status": "success",
            "message": f"Mapped to Lesson {mapping.lesson_number}",
            "lesson_number": mapping.lesson_number
        }
        
    except Exception as e:
        logger.error(f"Failed to save activity mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mapping/save-user-group")
async def save_user_group_mapping(mapping: UserGroupMapping):
    """Save a user to group mapping (stored separately)."""
    try:
        # Create user groups mapping file if it doesn't exist
        mapping_path = Path(__file__).parent.parent / "data" / "user_groups.json"
        
        if mapping_path.exists():
            with open(mapping_path, 'r') as f:
                data = json.load(f)
        else:
            data = {"user_groups": {}, "timestamp": datetime.now(timezone.utc).isoformat()}
        
        # Update user group
        data["user_groups"][mapping.actor_name] = mapping.group_name
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Save back to file
        with open(mapping_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Mapped user {mapping.actor_name} to group {mapping.group_name}")
        
        return {
            "status": "success",
            "message": f"User assigned to {mapping.group_name}",
            "group": mapping.group_name
        }
        
    except Exception as e:
        logger.error(f"Failed to save user group mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))

