"""
Settings UI for managing alert email addresses and other configuration.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from app.logging_config import get_logger
from app.services.alert_email_manager import alert_email_manager

logger = get_logger("settings_ui")
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class EmailRequest(BaseModel):
    """Request model for adding email."""
    email: EmailStr


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    """Settings page for managing alert emails and configuration."""
    try:
        emails = await alert_email_manager.get_all_emails()
        
        context = {
            "request": request,
            "active_page": "settings",
            "title": "Settings",
            "alert_emails": emails,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        raise HTTPException(status_code=500, detail=f"Settings page error: {str(e)}")


@router.get("/api/settings/alert-emails")
async def get_alert_emails() -> JSONResponse:
    """Get all alert email addresses."""
    try:
        emails = await alert_email_manager.get_all_emails()
        return JSONResponse({
            "success": True,
            "emails": emails
        })
    except Exception as e:
        logger.error(f"Failed to get alert emails: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/api/settings/alert-emails")
async def add_alert_email(request: EmailRequest) -> JSONResponse:
    """Add a new alert email address."""
    try:
        result = await alert_email_manager.add_email(request.email)
        if result.get("success"):
            return JSONResponse({
                "success": True,
                "message": f"Email {request.email} added successfully",
                "email": result.get("email")
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get("error", "Failed to add email")
            }, status_code=400)
    except Exception as e:
        logger.error(f"Failed to add alert email: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.delete("/api/settings/alert-emails/{email_id}")
async def delete_alert_email(email_id: str) -> JSONResponse:
    """Delete an alert email address."""
    try:
        result = await alert_email_manager.delete_email(email_id)
        if result.get("success"):
            return JSONResponse({
                "success": True,
                "message": "Email deleted successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get("error", "Failed to delete email")
            }, status_code=400)
    except Exception as e:
        logger.error(f"Failed to delete alert email: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

