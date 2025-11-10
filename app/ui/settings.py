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


@router.get("/api/settings/smtp-status")
async def get_smtp_status() -> JSONResponse:
    """Get SMTP configuration status."""
    import os
    
    smtp_server = os.getenv("ALERT_EMAIL_SMTP_SERVER")
    smtp_username = os.getenv("ALERT_EMAIL_SMTP_USERNAME")
    smtp_password = os.getenv("ALERT_EMAIL_SMTP_PASSWORD")
    smtp_port = os.getenv("ALERT_EMAIL_SMTP_PORT", "587")
    sender = os.getenv("ALERT_EMAIL_SENDER", "no-reply@practiceoflife.com")
    
    missing_vars = []
    if not smtp_server:
        missing_vars.append("ALERT_EMAIL_SMTP_SERVER")
    if not smtp_username:
        missing_vars.append("ALERT_EMAIL_SMTP_USERNAME")
    if not smtp_password:
        missing_vars.append("ALERT_EMAIL_SMTP_PASSWORD")
    
    configured = len(missing_vars) == 0
    
    return JSONResponse({
        "success": True,
        "configured": configured,
        "server": smtp_server if configured else None,
        "port": smtp_port,
        "sender": sender,
        "missing_vars": missing_vars if not configured else []
    })


@router.post("/api/settings/test-email")
async def test_email() -> JSONResponse:
    """Send a test email to verify SMTP configuration."""
    import os
    import smtplib
    import ssl
    from email.message import EmailMessage
    
    try:
        # Get SMTP config
        smtp_server = os.getenv("ALERT_EMAIL_SMTP_SERVER")
        smtp_username = os.getenv("ALERT_EMAIL_SMTP_USERNAME")
        smtp_password = os.getenv("ALERT_EMAIL_SMTP_PASSWORD")
        
        if not smtp_server or not smtp_username or not smtp_password:
            return JSONResponse({
                "success": False,
                "error": "SMTP not configured. Please set ALERT_EMAIL_SMTP_SERVER, ALERT_EMAIL_SMTP_USERNAME, and ALERT_EMAIL_SMTP_PASSWORD"
            }, status_code=400)
        
        # Get recipient emails
        recipient_emails = await alert_email_manager.get_active_emails()
        if not recipient_emails:
            return JSONResponse({
                "success": False,
                "error": "No alert email addresses configured"
            }, status_code=400)
        
        # Create test email
        sender = os.getenv("ALERT_EMAIL_SENDER", "no-reply@practiceoflife.com")
        subject = "🧪 POL Analytics - SMTP Test Email"
        
        body = f"""
This is a test email from POL Analytics.

If you received this email, your SMTP configuration is working correctly!

SMTP Server: {smtp_server}
Sender: {sender}
Timestamp: {datetime.now(timezone.utc).isoformat()}

---
POL Analytics Platform
"""
        
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipient_emails)
        message.set_content(body)
        
        # Send email
        port = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
        use_tls = os.getenv("ALERT_EMAIL_SMTP_USE_TLS", "true").lower() != "false"
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, port) as server:
            if use_tls:
                server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        
        logger.info(f"Test email sent successfully to {', '.join(recipient_emails)}")
        
        return JSONResponse({
            "success": True,
            "message": f"Test email sent to {', '.join(recipient_emails)}"
        })
        
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

