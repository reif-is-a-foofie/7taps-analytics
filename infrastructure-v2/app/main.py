"""
7taps Analytics v2 - Clean, Production-Ready FastAPI Application
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog
import time
import traceback
from typing import Dict, Any

from config.settings import settings
from app.api import health, analytics, xapi, monitoring, chat, data_explorer, public, etl
from app.ui import dashboard, admin, bigquery_dashboard, data_import, data_export, learninglocker_admin, statement_browser, user_management
from app.core.exceptions import AppException
from app.core.middleware import LoggingMiddleware, ErrorHandlingMiddleware


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Production-ready 7taps Analytics API",
    version="2.0.0",
    debug=settings.debug,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(xapi.router, prefix="/api/xapi", tags=["xAPI"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["Monitoring"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(data_explorer.router, tags=["Data Explorer"])
app.include_router(public.router, prefix="/api", tags=["Public API"])
app.include_router(etl.router, prefix="/api", tags=["ETL"])

# UI Routers
app.include_router(dashboard.router, tags=["Analytics Dashboard"])
app.include_router(admin.router, prefix="/ui", tags=["Admin Panel"])
app.include_router(bigquery_dashboard.router, prefix="/ui", tags=["BigQuery Dashboard"])
app.include_router(data_import.router, tags=["Data Import"])
app.include_router(data_export.router, tags=["Data Export"])
app.include_router(learninglocker_admin.router, prefix="/ui", tags=["Learning Locker Admin"])
app.include_router(statement_browser.router, prefix="/ui", tags=["Statement Browser"])
app.include_router(user_management.router, prefix="/ui", tags=["User Management"])


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with basic information."""
    return {
        "app": settings.app_name,
        "version": "2.0.0",
        "environment": settings.environment,
        "status": "healthy",
        "endpoints": {
            "health": "/api/health",
            "analytics": "/api/analytics",
            "xapi": "/api/xapi",
            "monitoring": "/api/monitoring",
            "docs": "/api/docs" if settings.debug else "disabled"
        }
    }


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.error(
        "Application exception",
        error=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "type": exc.__class__.__name__,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        "Unexpected exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        traceback=traceback.format_exc()
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": "InternalError",
            "path": request.url.path
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "Starting 7taps Analytics v2",
        environment=settings.environment,
        debug=settings.debug
    )
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )

