from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from app.config import settings

app = FastAPI(
    title="7taps Analytics ETL",
    description="Streaming ETL for xAPI analytics using direct database connections",
    version="1.0.0"
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

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Chat interface endpoint"""
    return templates.TemplateResponse("chat_interface.html", {
        "request": request,
        "active_page": "chat",
        "title": "AI Chat"
    })

@app.get("/docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    """API documentation endpoint"""
    return templates.TemplateResponse("docs.html", {
        "request": request,
        "active_page": "docs",
        "title": "API Documentation"
    })

@app.get("/explorer", response_class=HTMLResponse)
async def data_explorer(request: Request):
    """Serve the data explorer interface with template"""
    return templates.TemplateResponse("explorer.html", {
        "request": request,
        "active_page": "explorer",
        "title": "Data Explorer"
    })

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
                COUNT(DISTINCT ur.user_id) as users_completed,
                ROUND(
                    (COUNT(DISTINCT ur.user_id)::float / NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100)::numeric, 1
                ) as completion_rate
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            LEFT JOIN user_responses ur ON l.lesson_number = ur.lesson_number
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
        
        context = {
            "request": request,
            "active_page": "dashboard",
            "title": "Analytics Dashboard",
            "total_users": total_users,
            "total_activities": total_activities,
            "total_responses": total_responses,
            "total_questions": total_questions,
            "lesson_names": json.dumps(lesson_names),
            "completion_rates": json.dumps(completion_rates),
            "users_started": json.dumps(users_started),
            "users_completed": json.dumps(users_completed),
            "activity_dates": json.dumps(activity_dates),
            "activity_counts": json.dumps(activity_counts),
            "active_users": json.dumps(active_users),
            "response_type_labels": json.dumps(response_type_labels),
            "response_type_counts": json.dumps(response_type_counts)
        }
        
        return templates.TemplateResponse("dashboard.html", context)
        
    except Exception as e:
        # Return error page if database connection fails
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

# Import and include routers
try:
    from app.api.etl import router as etl_router
except Exception:
    etl_router = None
from app.api.orchestrator import router as orchestrator_router
# from app.api.nlp import router as nlp_router
from app.api.xapi import router as xapi_router
from app.api.seventaps import router as seventaps_router
from app.api.xapi_lrs import router as xapi_lrs_router
from app.api.learninglocker_sync import router as learninglocker_sync_router
from app.api.health import router as health_router
from app.api.data_normalization import router as data_normalization_router
from app.api.data_import import router as data_import_router
from app.api.migration import router as migration_router
from app.api.focus_group_import import router as focus_group_import_router
from app.api.csv_to_xapi import router as csv_to_xapi_router
from app.api.data_access import router as data_access_router
from app.api.chat import router as chat_router
from app.api.public import router as public_router
from app.api.public_data import router as public_data_router
from app.api.data_explorer import router as data_explorer_router
from app.api.dashboard import router as dashboard_router
from app.api.analytics import router as analytics_router
from app.ui.admin import router as admin_router
# from app.ui.dashboard import router as dashboard_router
from app.ui.data_import import router as data_import_ui_router
# from app.api.monitoring import router as monitoring_router
# from app.ui.production_dashboard import router as production_dashboard_router

# Internal/Admin routers - hidden from public API
# app.include_router(etl_router, prefix="/ui", tags=["ETL"])
app.include_router(orchestrator_router, prefix="/api", tags=["Orchestrator"])
# app.include_router(nlp_router, prefix="/api", tags=["NLP"])
# app.include_router(xapi_router, tags=["xAPI"])
# app.include_router(seventaps_router, tags=["7taps"])
# app.include_router(xapi_lrs_router, tags=["xAPI LRS"])
# app.include_router(learninglocker_sync_router, prefix="/api", tags=["Learning Locker"])
app.include_router(data_normalization_router, prefix="/api", tags=["Data Normalization"])
app.include_router(data_import_router, prefix="/api", tags=["Data Import"])
app.include_router(migration_router, prefix="/api", tags=["Migration"])
app.include_router(focus_group_import_router, prefix="/api", tags=["Focus Group Import"])
app.include_router(csv_to_xapi_router, prefix="/api", tags=["CSV to xAPI"])
app.include_router(data_access_router, prefix="/api", tags=["Data Access"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(dashboard_router, prefix="/api", tags=["Dashboard"])
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
# app.include_router(public_router, tags=["Public"])
# app.include_router(data_import_ui_router, tags=["Data Import UI"])
# app.include_router(admin_router, tags=["Admin"])
# app.include_router(dashboard_router, tags=["Dashboard"])
# app.include_router(monitoring_router, prefix="/api", tags=["Monitoring"])
# app.include_router(production_dashboard_router, tags=["Production Dashboard"])

# Public API - only essential data extraction endpoints
app.include_router(data_explorer_router, tags=["Data Explorer"])
app.include_router(health_router, tags=["Health"])
app.include_router(public_data_router, tags=["Public Data API"])

if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
