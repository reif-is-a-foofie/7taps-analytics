"""
Lean Production FastAPI App - Optimized for Fast Deploys
Only essential endpoints for production use.
"""

import os
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import with fallbacks for lean deployment
try:
    from app.config import settings
except ImportError:
    # Fallback config for lean deployment
    class Settings:
        ENVIRONMENT = "production"
        DEPLOYMENT_MODE = "cloud_run"
    settings = Settings()

try:
    from app.logging_config import get_logger
    logger = get_logger("lean_production")
except ImportError:
    import logging
    logger = logging.getLogger("lean_production")

# Initialize FastAPI app
app = FastAPI(
    title="7taps Analytics - Lean Production",
    description="Optimized production API for fast deployments",
    version="1.0.0"
)

logger = get_logger("lean_production")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Static files (if they exist)
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ============================================================================
# ESSENTIAL HEALTH ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - redirect to data explorer."""
    return {"message": "7taps Analytics - Lean Production", "status": "operational"}

@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/health")
async def api_health_check():
    """API health check."""
    return {
        "status": "operational",
        "service": "7taps-analytics",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================================
# ESSENTIAL UI ENDPOINTS
# ============================================================================

@app.get("/ui/data-explorer", response_class=HTMLResponse)
async def data_explorer_lean(request: Request):
    """Lean data explorer - core functionality only."""
    try:
        # Import only when needed
        from app.ui.pubsub_feed import data_explorer
        return await data_explorer(request, limit=25)
    except Exception as e:
        logger.error(f"Data explorer error: {e}")
        # Return simple HTML instead of template
        return HTMLResponse("""
        <html>
        <head><title>Data Explorer</title></head>
        <body>
            <h1>Data Explorer</h1>
            <p>Data explorer temporarily unavailable. Please try again later.</p>
            <p><a href="/api/health">Check Health</a></p>
        </body>
        </html>
        """)

@app.get("/ui/safety", response_class=HTMLResponse)
async def safety_dashboard_lean(request: Request):
    """Lean safety dashboard."""
    try:
        from app.ui.safety import get_safety_dashboard
        return await get_safety_dashboard(request)
    except Exception as e:
        logger.error(f"Safety dashboard error: {e}")
        return HTMLResponse("""
        <html>
        <head><title>Safety Dashboard</title></head>
        <body>
            <h1>Safety Dashboard</h1>
            <p>Safety dashboard temporarily unavailable. Please try again later.</p>
            <p><a href="/api/health">Check Health</a></p>
        </body>
        </html>
        """)

# ============================================================================
# ESSENTIAL API ENDPOINTS
# ============================================================================

@app.post("/api/xapi/statements")
async def ingest_xapi_lean(request: Request):
    """Lean xAPI ingestion - core functionality only."""
    try:
        from app.api.xapi import ingest_xapi_statements
        return await ingest_xapi_statements(request)
    except Exception as e:
        logger.error(f"xAPI ingestion error: {e}")
        raise HTTPException(status_code=500, detail="Ingestion temporarily unavailable")

@app.get("/api/xapi/recent")
async def recent_statements_lean():
    """Lean recent statements endpoint."""
    try:
        from app.api.xapi import get_recent_statements
        return await get_recent_statements()
    except Exception as e:
        logger.error(f"Recent statements error: {e}")
        raise HTTPException(status_code=500, detail="Recent statements temporarily unavailable")

# ============================================================================
# AI SERVICE INTEGRATION (Lean)
# ============================================================================

@app.post("/api/ai-content/analyze")
async def analyze_content_lean(request: Request):
    """Lean AI content analysis using external service."""
    try:
        from app.services.ai_service_client import ai_service_client
        data = await request.json()
        result = await ai_service_client.analyze_content(
            content=data.get("content", ""),
            context=data.get("context", "general")
        )
        return result
    except Exception as e:
        logger.error(f"AI analysis error: {e}")
        return {"error": "AI analysis temporarily unavailable", "fallback": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
