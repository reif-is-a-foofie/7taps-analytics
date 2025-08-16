from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
import os
import sys
import traceback
import time
from contextlib import asynccontextmanager
from app.config import settings
from app.logging_config import get_logger, log_performance, error_tracker

# Initialize logger
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with comprehensive logging."""
    logger.info("application_starting", environment=settings.ENVIRONMENT)
    
    try:
        # Log startup configuration
        logger.info(
            "startup_configuration",
            database_url=get_database_url_safe(),
            redis_url=get_redis_url_safe(),
            debug=settings.DEBUG,
            log_level=settings.LOG_LEVEL
        )
        
        # Test database connections
        await test_database_connections()
        
        logger.info("application_started_successfully")
        yield
        
    except Exception as e:
        logger.critical("application_startup_failed", error=str(e), traceback=traceback.format_exc())
        raise
    finally:
        logger.info("application_shutting_down")

def get_database_url_safe():
    """Get database URL for logging (sanitized)."""
    db_url = settings.DATABASE_URL
    if db_url and '@' in db_url:
        # Mask password in URL
        parts = db_url.split('@')
        if len(parts) == 2:
            auth_part = parts[0]
            if ':' in auth_part:
                user_pass = auth_part.split(':')
                if len(user_pass) >= 3:  # postgresql://user:pass@host
                    return f"{user_pass[0]}:{user_pass[1]}:***@{parts[1]}"
    return "***" if db_url else "not_set"

def get_redis_url_safe():
    """Get Redis URL for logging (sanitized)."""
    redis_url = settings.REDIS_URL
    if redis_url and '@' in redis_url:
        # Mask password in URL
        parts = redis_url.split('@')
        if len(parts) == 2:
            auth_part = parts[0]
            if ':' in auth_part:
                user_pass = auth_part.split(':')
                if len(user_pass) >= 3:  # redis://user:pass@host
                    return f"{user_pass[0]}:{user_pass[1]}:***@{parts[1]}"
    return "***" if redis_url else "not_set"

async def test_database_connections():
    """Test database connections on startup."""
    logger.info("testing_database_connections")
    
    # Test PostgreSQL connection
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        db_url = settings.DATABASE_URL
        if db_url:
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            conn.close()
            logger.info("postgresql_connection_successful")
        else:
            logger.warning("postgresql_url_not_configured")
    except Exception as e:
        logger.warning("postgresql_connection_failed", error=str(e))
        # Don't fail startup for database connection issues
    
    # Test Redis connection - make this optional
    try:
        import redis
        from urllib.parse import urlparse
        
        redis_url = settings.REDIS_URL
        if redis_url:
            parsed = urlparse(redis_url)
            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port or 6379,
                password=parsed.password,
                decode_responses=True,
                socket_connect_timeout=5,  # Short timeout
                socket_timeout=5
            )
            r.ping()
            logger.info("redis_connection_successful")
        else:
            logger.warning("redis_url_not_configured")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))
        # Don't fail startup for Redis connection issues - it's optional for basic functionality

app = FastAPI(
    title="7taps Analytics ETL",
    description="Streaming ETL for xAPI analytics using direct database connections",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with performance metrics."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            duration_ms=round(duration * 1000, 2)
        )
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with comprehensive logging."""
    error_tracker.track_error(exc, {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None
    })
    
    logger.error(
        "unhandled_exception",
        method=request.method,
        url=str(request.url),
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc()
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger.warning(
        "validation_error",
        method=request.method,
        url=str(request.url),
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors()
        }
    )

@app.get("/", response_class=HTMLResponse)
@log_performance("root_endpoint")
async def root():
    """Root endpoint with HTML landing page"""
    logger.info("root_endpoint_accessed")
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>7taps Analytics ETL</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 50px;
            }
            .header h1 {
                font-size: 3em;
                margin: 0;
                font-weight: 300;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
                margin: 10px 0 0 0;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 30px;
                margin-bottom: 40px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                transition: transform 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
            }
            .card h2 {
                color: #667eea;
                margin: 0 0 15px 0;
                font-size: 1.5em;
            }
            .card p {
                color: #666;
                line-height: 1.6;
                margin: 0 0 20px 0;
            }
            .btn {
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .status {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
            }
            .status h3 {
                color: #28a745;
                margin: 0 0 10px 0;
            }
            .status p {
                margin: 5px 0;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>7taps Analytics ETL</h1>
                <p>Streaming ETL for xAPI analytics using direct database connections</p>
            </div>
            
            <div class="status">
                <h3>✅ System Status: Operational</h3>
                <p><strong>Environment:</strong> """ + settings.ENVIRONMENT + """</p>
                <p><strong>Version:</strong> 1.0.0</p>
                <p><strong>Database:</strong> """ + ("Connected" if settings.DATABASE_URL else "Not Configured") + """</p>
                <p><strong>Redis:</strong> """ + ("Connected" if settings.REDIS_URL else "Not Configured") + """</p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h2>📊 Analytics Dashboard</h2>
                    <p>View real-time analytics and insights from your xAPI data.</p>
                    <a href="/ui/dashboard" class="btn">Open Dashboard</a>
                </div>
                
                <div class="card">
                    <h2>🔍 SQL Query Terminal</h2>
                    <p>Execute SQL queries directly against your analytics database.</p>
                    <a href="/ui/sql-query" class="btn">Open Terminal</a>
                </div>
                
                <div class="card">
                    <h2>📝 xAPI Statement Browser</h2>
                    <p>Browse and search through xAPI statements in your system.</p>
                    <a href="/ui/statement-browser" class="btn">Browse Statements</a>
                </div>
                
                <div class="card">
                    <h2>⚙️ System Health</h2>
                    <p>Monitor system health, performance, and error rates.</p>
                    <a href="/health" class="btn">Check Health</a>
                </div>
                
                <div class="card">
                    <h2>📈 ETL Monitoring</h2>
                    <p>Monitor ETL processes and data pipeline status.</p>
                    <a href="/ui/etl-monitoring" class="btn">Monitor ETL</a>
                </div>
                
                <div class="card">
                    <h2>🔧 API Documentation</h2>
                    <p>Explore the API endpoints and test functionality.</p>
                    <a href="/docs" class="btn">View API Docs</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/health")
@log_performance("health_check")
async def health_check():
    """Comprehensive health check endpoint."""
    logger.info("health_check_requested")
    
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "services": {}
    }
    
    # Check database connection
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        db_url = settings.DATABASE_URL
        if db_url:
            parsed = urlparse(db_url)
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            conn.close()
            health_status["services"]["database"] = "healthy"
            logger.info("health_check_database_healthy")
        else:
            health_status["services"]["database"] = "not_configured"
            logger.warning("health_check_database_not_configured")
    except Exception as e:
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error("health_check_database_unhealthy", error=str(e))
    
    # Check Redis connection
    try:
        import redis
        from urllib.parse import urlparse
        
        redis_url = settings.REDIS_URL
        if redis_url:
            parsed = urlparse(redis_url)
            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port or 6379,
                password=parsed.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            r.ping()
            health_status["services"]["redis"] = "healthy"
            logger.info("health_check_redis_healthy")
        else:
            health_status["services"]["redis"] = "not_configured"
            logger.warning("health_check_redis_not_configured")
    except Exception as e:
        health_status["services"]["redis"] = "unhealthy"
        # Don't mark overall status as degraded for Redis issues
        logger.warning("health_check_redis_unhealthy", error=str(e))
    
    # Add error statistics
    error_stats = error_tracker.get_error_stats()
    health_status["error_stats"] = error_stats
    
    logger.info("health_check_completed", status=health_status["status"])
    
    return health_status

@app.get("/debug/info")
async def debug_info():
    """Debug information endpoint (development only)."""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Debug endpoint not available in production")
    
    logger.info("debug_info_requested")
    
    debug_info = {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "python_version": sys.version,
        "environment_variables": {
            "DATABASE_URL": "***" if settings.DATABASE_URL else None,
            "REDIS_URL": "***" if settings.REDIS_URL else None,
            "ENVIRONMENT": settings.ENVIRONMENT,
            "DEBUG": settings.DEBUG
        },
        "error_stats": error_tracker.get_error_stats()
    }
    
    return debug_info

# Import and include routers - DEPLOYMENT FIX IN PROGRESS
try:
    from app.api import health, seventaps, xapi, orchestrator
    from app.ui import dashboard, admin, data_export, data_import, enhanced_dashboard, learninglocker_admin, production_dashboard, sql_query, statement_browser, user_management
    
    # Include API routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(seventaps.router, prefix="/api/7taps", tags=["7taps"])
    app.include_router(xapi.router, prefix="/api/xapi", tags=["xAPI"])
    app.include_router(orchestrator.router, prefix="/api", tags=["Orchestrator"])
    
    # Include UI routers
    app.include_router(dashboard.router, prefix="/ui", tags=["UI"])
    app.include_router(admin.router, prefix="/ui", tags=["UI"])
    app.include_router(data_export.router, prefix="/ui", tags=["UI"])
    app.include_router(data_import.router, prefix="/ui", tags=["UI"])
    app.include_router(enhanced_dashboard.router, prefix="/ui", tags=["UI"])
    app.include_router(learninglocker_admin.router, prefix="/ui", tags=["UI"])
    app.include_router(production_dashboard.router, prefix="/ui", tags=["UI"])
    app.include_router(sql_query.router, prefix="/ui", tags=["UI"])
    app.include_router(statement_browser.router, prefix="/ui", tags=["UI"])
    app.include_router(user_management.router, prefix="/ui", tags=["UI"])
    
    logger.info("all_routers_loaded_successfully")
    
except ImportError as e:
    logger.error("failed_to_import_router", router=str(e), traceback=traceback.format_exc())
    # Continue without the router - this allows the app to start even if some modules are missing

if __name__ == "__main__":
    import uvicorn
    logger.info("starting_application_directly")
    uvicorn.run(app, host="0.0.0.0", port=8000) 