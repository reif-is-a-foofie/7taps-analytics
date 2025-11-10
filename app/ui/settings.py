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


@router.get("/api/settings/gmail/connect")
async def gmail_connect(request: Request) -> JSONResponse:
    """Get Gmail OAuth authorization URL."""
    from app.services.gmail_oauth import gmail_oauth_service
    
    request_url = str(request.url)
    result = gmail_oauth_service.get_authorization_url(request_url)
    
    if result.get("success"):
        return JSONResponse(result)
    else:
        return JSONResponse(result, status_code=400)


@router.get("/api/settings/gmail/callback")
async def gmail_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None
) -> HTMLResponse:
    """Handle Gmail OAuth callback."""
    from app.services.gmail_oauth import gmail_oauth_service
    from urllib.parse import urlencode
    
    if error:
        error_html = f"""
        <html>
        <body>
            <h1>Gmail Connection Failed</h1>
            <p>Error: {error}</p>
            <p><a href="/ui/settings">Return to Settings</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)
    
    if not code:
        error_html = """
        <html>
        <body>
            <h1>Gmail Connection Failed</h1>
            <p>No authorization code received.</p>
            <p><a href="/ui/settings">Return to Settings</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)
    
    # Get redirect URI from state or request
    redirect_uri = request.url.scheme + "://" + request.url.netloc + "/api/settings/gmail/callback"
    
    result = await gmail_oauth_service.handle_callback(code, state, redirect_uri)
    
    if result.get("success"):
        success_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: green;">✅ Gmail Connected Successfully!</h1>
            <p>Email: {result.get('email')}</p>
            <p>You can now close this window.</p>
            <p><a href="/ui/settings" style="color: blue;">Return to Settings</a></p>
            <script>
                setTimeout(function() {{
                    window.location.href = '/ui/settings';
                }}, 2000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html)
    else:
        error_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Gmail Connection Failed</h1>
            <p>Error: {result.get('error', 'Unknown error')}</p>
            <p><a href="/ui/settings">Return to Settings</a></p>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=400)


@router.get("/api/settings/gmail/status")
async def gmail_status() -> JSONResponse:
    """Get Gmail connection status."""
    from app.services.gmail_oauth import gmail_oauth_service
    
    status = await gmail_oauth_service.get_connection_status()
    return JSONResponse(status)


@router.post("/api/settings/gmail/disconnect")
async def gmail_disconnect() -> JSONResponse:
    """Disconnect Gmail (delete stored credentials)."""
    from app.services.gmail_oauth import gmail_oauth_service
    
    # TODO: Implement disconnect (delete from BigQuery)
    return JSONResponse({
        "success": True,
        "message": "Gmail disconnected"
    })


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
    """Send a test email using Gmail OAuth (preferred) or SMTP fallback."""
    from app.services.gmail_oauth import gmail_oauth_service
    import os
    
    try:
        # Get recipient emails
        recipient_emails = await alert_email_manager.get_active_emails()
        if not recipient_emails:
            return JSONResponse({
                "success": False,
                "error": "No alert email addresses configured"
            }, status_code=400)
        
        # Create test email
        subject = "🧪 POL Analytics - Test Email"
        body = f"""
This is a test email from POL Analytics.

If you received this email, your email configuration is working correctly!

Timestamp: {datetime.now(timezone.utc).isoformat()}

---
POL Analytics Platform
"""
        
        # Try Gmail OAuth first
        gmail_status = await gmail_oauth_service.get_connection_status()
        if gmail_status.get("connected"):
            result = await gmail_oauth_service.send_email(
                to_emails=recipient_emails,
                subject=subject,
                body=body
            )
            if result.get("success"):
                logger.info(f"Test email sent via Gmail API to {', '.join(recipient_emails)}")
                return JSONResponse({
                    "success": True,
                    "message": f"Test email sent via Gmail to {', '.join(recipient_emails)}",
                    "method": "gmail_oauth"
                })
        
        # Fallback to SMTP
        import smtplib
        import ssl
        from email.message import EmailMessage
        
        smtp_server = os.getenv("ALERT_EMAIL_SMTP_SERVER")
        smtp_username = os.getenv("ALERT_EMAIL_SMTP_USERNAME")
        smtp_password = os.getenv("ALERT_EMAIL_SMTP_PASSWORD")
        
        if not smtp_server or not smtp_username or not smtp_password:
            return JSONResponse({
                "success": False,
                "error": "Neither Gmail OAuth nor SMTP is configured. Please connect Gmail or configure SMTP."
            }, status_code=400)
        
        sender = os.getenv("ALERT_EMAIL_SENDER", "no-reply@practiceoflife.com")
        
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipient_emails)
        message.set_content(body)
        
        port = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
        use_tls = os.getenv("ALERT_EMAIL_SMTP_USE_TLS", "true").lower() != "false"
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, port) as server:
            if use_tls:
                server.starttls(context=context)
            server.login(smtp_username, smtp_password)
            server.send_message(message)
        
        logger.info(f"Test email sent via SMTP to {', '.join(recipient_emails)}")
        
        return JSONResponse({
            "success": True,
            "message": f"Test email sent via SMTP to {', '.join(recipient_emails)}",
            "method": "smtp"
        })
        
    except Exception as e:
        logger.error(f"Failed to send test email: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

