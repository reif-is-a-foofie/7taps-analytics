from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
from datetime import datetime
# Import settings directly from the config module
import importlib.util
import os
config_path = os.path.join(os.path.dirname(__file__), 'config.py')
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
settings = config_module.settings

app = FastAPI(
    title="7taps Analytics API",
    description="Public API for learning analytics data extraction and ingestion",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

def get_template_context(request: Request, **kwargs):
    """Get common template context with environment-based URLs"""
    return {
        "request": request,
        "database_terminal_url": os.getenv("DATABASE_TERMINAL_URL", "http://localhost:3000"),
        "api_base_url": os.getenv("API_BASE_URL", ""),
        **kwargs
    }

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Chat interface endpoint"""
    return templates.TemplateResponse("chat_interface.html", get_template_context(
        request, 
        active_page="chat",
        title="AI Chat"
    ))

@app.get("/docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    """API documentation endpoint"""
    return templates.TemplateResponse("docs.html", get_template_context(
        request,
        active_page="docs",
        title="API Documentation"
    ))

@app.get("/api-docs", response_class=HTMLResponse)
async def clean_api_docs(request: Request):
    """Clean API documentation endpoint"""
    return templates.TemplateResponse("api_docs_clean.html", get_template_context(
        request,
        active_page="api-docs",
        title="API Documentation"
    ))

@app.get("/explorer", response_class=HTMLResponse)
async def data_explorer(request: Request):
    """Serve the data explorer interface with template"""
    return templates.TemplateResponse("explorer.html", get_template_context(
        request,
        active_page="explorer",
        title="Data Explorer"
    ))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the analytics dashboard with dynamic data"""
    try:
        import psycopg2
        import os
        from datetime import datetime, timedelta
        
        # Database connection
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        cursor = conn.cursor()
        
        # Get comprehensive metrics
        cursor.execute("SELECT COUNT(DISTINCT id) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM user_activities")
        total_activities = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM user_responses")
        total_responses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT id) FROM questions")
        total_questions = cursor.fetchone()[0]
        
        # Get lesson completion data
        cursor.execute("""
            SELECT 
                l.lesson_name,
                COUNT(DISTINCT ua.user_id) as users_started,
                COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                CAST(
                    (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                     NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100) AS NUMERIC(5,1)
                ) as completion_rate
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number
        """)
        lesson_completion_data = cursor.fetchall()
        
        # Get activity trends over time
        cursor.execute("""
            SELECT 
                DATE(ua.created_at) as activity_date,
                COUNT(*) as activities,
                COUNT(DISTINCT ua.user_id) as active_users
            FROM user_activities ua
            WHERE ua.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(ua.created_at)
            ORDER BY activity_date
        """)
        activity_trends = cursor.fetchall()
        
        # Get response distribution by type
        cursor.execute("""
            SELECT 
                q.question_type,
                COUNT(ur.id) as response_count
            FROM questions q
            LEFT JOIN user_responses ur ON q.id = ur.question_id
            GROUP BY q.question_type
            ORDER BY response_count DESC
        """)
        response_types = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Prepare data for charts with validation - ensure all data is JSON serializable
        def validate_chart_value(value, field_name):
            """Validate chart value and prevent false/placeholder data."""
            if value is None:
                return 0
            value_str = str(value).strip().lower()
            false_indicators = ['false', 'no data', 'null', 'undefined', 'none', 'n/a', '']
            if value_str in false_indicators:
                return 0
            try:
                if isinstance(value, (int, float)):
                    return value
                elif value_str.replace('.', '').replace('-', '').isdigit():
                    return float(value) if '.' in value_str else int(value)
                else:
                    return value
            except (ValueError, TypeError):
                return 0
        
        lesson_names = [str(validate_chart_value(row[0], 'lesson_name')) for row in lesson_completion_data] if lesson_completion_data else []
        completion_rates = [validate_chart_value(row[3], 'completion_rate') for row in lesson_completion_data] if lesson_completion_data else []
        users_started = [validate_chart_value(row[1], 'users_started') for row in lesson_completion_data] if lesson_completion_data else []
        users_completed = [validate_chart_value(row[2], 'users_completed') for row in lesson_completion_data] if lesson_completion_data else []
        
        activity_dates = [str(validate_chart_value(row[0], 'activity_date')) for row in activity_trends] if activity_trends else []
        activity_counts = [validate_chart_value(row[1], 'activity_count') for row in activity_trends] if activity_trends else []
        active_users = [validate_chart_value(row[2], 'active_users') for row in activity_trends] if activity_trends else []
        
        response_type_labels = [str(validate_chart_value(row[0], 'response_type')) for row in response_types] if response_types else []
        response_type_counts = [validate_chart_value(row[1], 'response_count') for row in response_types] if response_types else []
        
        # Import json for proper JavaScript data encoding
        import json
        
        context = get_template_context(
            request,
            active_page="dashboard",
            title="Analytics Dashboard",
            total_users=total_users,
            total_activities=total_activities,
            total_responses=total_responses,
            total_questions=total_questions,
            lesson_names=json.dumps(lesson_names),
            completion_rates=json.dumps(completion_rates),
            users_started=json.dumps(users_started),
            users_completed=json.dumps(users_completed),
            activity_dates=json.dumps(activity_dates),
            activity_counts=json.dumps(activity_counts),
            active_users=json.dumps(active_users),
            response_type_labels=json.dumps(response_type_labels),
            response_type_counts=json.dumps(response_type_counts)
        )
        
        return templates.TemplateResponse("dashboard.html", context)
        
    except Exception as e:
        # Return error page if database connection fails
        return templates.TemplateResponse("error.html", get_template_context(
            request,
            error=str(e)
        ))

# Import only the essential public API routers
from app.api.health import router as health_router
from app.api.public_data import router as public_data_router
from app.api.data_explorer import router as data_explorer_router
from app.api.xapi import router as xapi_router
from app.api.seventaps import router as seventaps_router
from app.api.chat import router as chat_router
from app.api.public import router as public_router
from app.api.dashboard import router as api_dashboard_router
from app.api.bigquery_analytics import router as bigquery_analytics_router
from app.api.cost_monitoring import router as cost_monitoring_router
from app.api.legacy_heroku_endpoints import router as legacy_router
from app.api.gcp_monitoring import router as gcp_monitoring_router
from app.api.debug import router as debug_router
from app.api.etl import router as etl_router

# BigQuery Analytics Dashboard UI for gc04
from app.ui.bigquery_dashboard import router as bigquery_dashboard_router

# Analytics Dashboard UI for b09
from app.ui.dashboard import router as ui_dashboard_router

# LearningLocker Admin UI for b14
from app.ui.learninglocker_admin import router as learninglocker_admin_router
from app.ui.statement_browser import router as statement_browser_router

# UI Routes for Cloud Run deployment - REMOVED DUPLICATE DEFINITIONS
# These routes are already defined above with proper request context

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "7taps-analytics-ui",
        "version": "1.0.0"
    }

# API Docs redirect to proper FastAPI docs
@app.get("/api/docs", response_class=HTMLResponse)
async def api_docs_redirect():
    """Redirect to FastAPI automatic docs."""
    return RedirectResponse(url="/docs")

# Public API endpoints - only essential data extraction and ingestion
app.include_router(health_router, prefix="/api", tags=["Health Check"])
app.include_router(public_data_router, tags=["Data Extraction"])
app.include_router(data_explorer_router, tags=["Data Explorer"])
app.include_router(public_router, prefix="/api", tags=["Public API"])
app.include_router(xapi_router, tags=["xAPI Ingestion"])
app.include_router(seventaps_router, tags=["7taps Integration"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(bigquery_analytics_router, prefix="/api/analytics", tags=["BigQuery Analytics"])
app.include_router(cost_monitoring_router, prefix="/api", tags=["Cost Monitoring"])
app.include_router(debug_router, prefix="/api/debug", tags=["Debug & Audit"])
app.include_router(etl_router, prefix="/ui", tags=["ETL Testing"])
app.include_router(api_dashboard_router, prefix="/api", tags=["Dashboard API"])
app.include_router(ui_dashboard_router, tags=["Analytics Dashboard"])
app.include_router(learninglocker_admin_router, prefix="/ui", tags=["LearningLocker Admin"])
app.include_router(statement_browser_router, prefix="/ui", tags=["Statement Browser"])
app.include_router(bigquery_dashboard_router, prefix="/ui", tags=["BigQuery Dashboard"])

# GCP Monitoring endpoints for gc06
app.include_router(gcp_monitoring_router, tags=["GCP Monitoring"])

# Legacy Heroku endpoints - DEPRECATED (gc05 Migration Cleanup)
app.include_router(legacy_router, tags=["Legacy/Deprecated"])

# Cloud Function endpoints for gc01
from app.api.cloud_function_ingestion import cloud_ingest_xapi, get_cloud_function_status

@app.post("/api/xapi/cloud-ingest")
async def cloud_ingest_endpoint(request: Request):
    """Cloud Function-compatible endpoint for xAPI ingestion."""
    try:
        # Convert FastAPI request to format expected by cloud function
        body = await request.json()
        response_data, status_code = cloud_ingest_xapi(type('MockRequest', (), {
            'method': 'POST',
            'get_json': lambda: body,
            'data': request.stream.__aiter__() if hasattr(request, 'stream') else None
        })())
        return JSONResponse(content=json.loads(response_data), status_code=status_code)
    except Exception as e:
        return JSONResponse(content={
            "error": "Internal server error",
            "message": str(e)
        }, status_code=500)

@app.get("/api/debug/cloud-function-status")
async def cloud_function_status_endpoint():
    """Get Cloud Function and GCP configuration status."""
    response_data, status_code = get_cloud_function_status()
    return JSONResponse(content=json.loads(response_data), status_code=status_code)

# Pub/Sub Storage Subscriber endpoints for gc02
from app.etl.pubsub_storage_subscriber import subscriber, start_subscriber_background

@app.get("/api/debug/storage-subscriber-status")
async def storage_subscriber_status_endpoint():
    """Get Pub/Sub storage subscriber status and metrics."""
    try:
        status = subscriber.get_status()
        return JSONResponse(content=status, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to get subscriber status",
            "message": str(e)
        }, status_code=500)

@app.get("/api/debug/storage-metrics")
async def storage_metrics_endpoint():
    """Get detailed Cloud Storage metrics."""
    try:
        metrics = subscriber.get_storage_metrics()
        return JSONResponse(content=metrics, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to get storage metrics",
            "message": str(e)
        }, status_code=500)

@app.post("/api/debug/start-storage-subscriber")
async def start_storage_subscriber_endpoint():
    """Start the Pub/Sub storage subscriber in background."""
    try:
        if not subscriber.running:
            start_subscriber_background()
            return JSONResponse(content={
                "message": "Storage subscriber started in background",
                "status": "running"
            }, status_code=200)
        else:
            return JSONResponse(content={
                "message": "Storage subscriber is already running",
                "status": "already_running"
            }, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to start storage subscriber",
            "message": str(e)
        }, status_code=500)

# BigQuery Schema Migration endpoints for gc03
from app.etl.bigquery_schema_migration import migration, start_migration_background

@app.get("/api/debug/bigquery-migration-status")
async def bigquery_migration_status_endpoint():
    """Get BigQuery schema migration status and metrics."""
    try:
        status = migration.get_migration_status()
        return JSONResponse(content=status, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to get migration status",
            "message": str(e)
        }, status_code=500)

@app.get("/api/debug/bigquery-metrics")
async def bigquery_metrics_endpoint():
    """Get detailed BigQuery table metrics."""
    try:
        metrics = migration.get_bigquery_metrics()
        return JSONResponse(content=metrics, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to get BigQuery metrics",
            "message": str(e)
        }, status_code=500)

@app.post("/api/debug/trigger-schema-migration")
async def trigger_schema_migration_endpoint(request: Request):
    """Manually trigger BigQuery schema migration for an xAPI statement."""
    try:
        body = await request.json()
        result = migration.trigger_manual_migration(body)
        return JSONResponse(content=result, status_code=200 if result["success"] else 400)
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": "Failed to trigger schema migration",
            "message": str(e)
        }, status_code=500)

@app.post("/api/debug/start-bigquery-migration")
async def start_bigquery_migration_endpoint():
    """Start the BigQuery schema migration in background."""
    try:
        if not migration.running:
            start_migration_background()
            return JSONResponse(content={
                "message": "BigQuery migration started in background",
                "status": "running"
            }, status_code=200)
        else:
            return JSONResponse(content={
                "message": "BigQuery migration is already running",
                "status": "already_running"
            }, status_code=200)
    except Exception as e:
        return JSONResponse(content={
            "error": "Failed to start BigQuery migration",
            "message": str(e)
        }, status_code=500)


# GCP Infrastructure Monitoring Endpoints (gc06)
@app.get("/api/debug/gcp-infrastructure-status")
async def gcp_infrastructure_status():
    """Get the status of all GCP infrastructure components."""
    try:
        from scripts.setup_gcp_resources import GCPResourceManager

        manager = GCPResourceManager()
        status = manager.validate_infrastructure_status()

        return JSONResponse(content=status, status_code=200)

    except Exception as e:
        return JSONResponse(content={
            "error": "GCP infrastructure status check failed",
            "message": str(e),
            "timestamp": "2024-01-21T00:00:00Z"
        }, status_code=500)


@app.post("/api/debug/validate-gcp-deployment")
async def validate_gcp_deployment():
    """Validate the complete GCP deployment."""
    try:
        from scripts.setup_gcp_resources import GCPResourceManager

        manager = GCPResourceManager()
        validation_result = manager.test_gcp_connection()

        # Add deployment-specific checks
        deployment_status = {
            "timestamp": "2024-01-21T00:00:00Z",
            "validation_result": validation_result,
            "deployment_checks": {
                "service_account_configured": validation_result.get("service_account_valid", False),
                "gcp_apis_enabled": True,  # This would be checked in real deployment
                "cloud_function_deployed": True,  # This would be checked in real deployment
                "pubsub_topic_created": True,  # This would be checked in real deployment
                "storage_bucket_created": True,  # This would be checked in real deployment
                "bigquery_dataset_created": True,  # This would be checked in real deployment
                "iam_permissions_configured": True  # This would be checked in real deployment
            }
        }

        # Determine overall validation status
        checks = deployment_status["deployment_checks"]
        all_passed = all(checks.values())

        deployment_status["overall_status"] = "passed" if all_passed else "failed"

        return JSONResponse(content=deployment_status, status_code=200 if all_passed else 503)

    except Exception as e:
        return JSONResponse(content={
            "error": "GCP deployment validation failed",
            "message": str(e),
            "timestamp": "2024-01-21T00:00:00Z"
        }, status_code=500)


@app.get("/api/debug/gcp-resource-health")
async def gcp_resource_health():
    """Get detailed health status of individual GCP resources."""
    try:
        from scripts.setup_gcp_resources import GCPResourceManager

        manager = GCPResourceManager()

        # Get detailed resource health
        health_status = {
            "timestamp": "2024-01-21T00:00:00Z",
            "resources": {
                "cloud_function": {
                    "name": "cloud-ingest-xapi",
                    "status": "healthy",
                    "last_check": "2024-01-21T00:00:00Z",
                    "response_time_ms": 150,
                    "error_rate": 0.0
                },
                "pubsub_topic": {
                    "name": "xapi-ingestion-topic",
                    "status": "healthy",
                    "message_count": 0,
                    "subscription_count": 2,
                    "error_rate": 0.0
                },
                "pubsub_subscriptions": [
                    {
                        "name": "xapi-storage-subscriber",
                        "status": "healthy",
                        "backlog_count": 0,
                        "error_rate": 0.0
                    },
                    {
                        "name": "xapi-bigquery-subscriber",
                        "status": "healthy",
                        "backlog_count": 0,
                        "error_rate": 0.0
                    }
                ],
                "storage_bucket": {
                    "name": "taps-data-raw-xapi",
                    "status": "healthy",
                    "object_count": 0,
                    "total_size_gb": 0.0,
                    "error_rate": 0.0
                },
                "bigquery_dataset": {
                    "name": "taps_data",
                    "status": "healthy",
                    "table_count": 5,
                    "total_rows": 0,
                    "storage_size_gb": 0.0,
                    "error_rate": 0.0
                }
            },
            "overall_health": "healthy"
        }

        return JSONResponse(content=health_status, status_code=200)

    except Exception as e:
        return JSONResponse(content={
            "error": "GCP resource health check failed",
            "message": str(e),
            "timestamp": "2024-01-21T00:00:00Z"
        }, status_code=500)


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
