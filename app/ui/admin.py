from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Templates setup
templates = Jinja2Templates(directory="templates")

class DBQueryRequest(BaseModel):
    query: str
    query_type: str = "analytics"  # cohort, completion, analytics, custom

class DBQueryResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    row_count: int
    execution_time: float
    error: Optional[str] = None

class PrebuiltQuery(BaseModel):
    name: str
    description: str
    sql: str
    category: str

class AdminPanelConfig:
    def __init__(self):
        self.sqlpad_url = os.getenv("SQLPAD_URL", "http://localhost:3000")
        self.superset_url = os.getenv("SUPERSET_URL", "http://localhost:8088")
        self.database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/7taps_analytics")
        self.use_sqlpad = os.getenv("USE_SQLPAD", "true").lower() == "true"
        
    def get_db_terminal_url(self) -> str:
        """Get the appropriate DB terminal URL"""
        if self.use_sqlpad:
            return f"{self.sqlpad_url}/query"
        else:
            return f"{self.superset_url}/superset/sqllab"

# Initialize config
admin_config = AdminPanelConfig()

# Prebuilt queries for common analytics
PREBUILT_QUERIES = [
    PrebuiltQuery(
        name="Unified Data Overview",
        description="Overview of data from both xAPI and CSV sources",
        sql="""
        SELECT 
            source,
            COUNT(*) as total_statements,
            COUNT(DISTINCT actor_id) as unique_learners,
            COUNT(DISTINCT activity_id) as unique_activities,
            MIN(timestamp) as earliest_activity,
            MAX(timestamp) as latest_activity
        FROM statements_new
        GROUP BY source
        ORDER BY total_statements DESC
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Focus Group Responses by Lesson",
        description="CSV focus group data organized by lesson number",
        sql="""
        SELECT 
            ce.extension_value as lesson_number,
            COUNT(*) as response_count,
            COUNT(DISTINCT s.actor_id) as unique_learners,
            COUNT(DISTINCT ce2.extension_value) as card_types
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        LEFT JOIN context_extensions_new ce2 ON s.statement_id = ce2.statement_id 
            AND ce2.extension_key = 'https://7taps.com/card-type'
        WHERE s.source = 'csv' 
            AND ce.extension_key = 'https://7taps.com/lesson-number'
        GROUP BY ce.extension_value
        ORDER BY lesson_number::integer
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="xAPI Activity Patterns",
        description="Real-time xAPI learning activity patterns",
        sql="""
        SELECT 
            verb_id,
            COUNT(*) as activity_count,
            COUNT(DISTINCT actor_id) as unique_learners,
            COUNT(DISTINCT activity_id) as unique_activities,
            AVG(EXTRACT(EPOCH FROM (NOW() - timestamp))/3600) as hours_since_last_activity
        FROM statements_new
        WHERE source = 'xapi'
        GROUP BY verb_id
        ORDER BY activity_count DESC
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Learner Engagement by Source",
        description="Compare learner engagement across xAPI and CSV sources",
        sql="""
        SELECT 
            s.source,
            s.actor_id,
            COUNT(*) as total_activities,
            COUNT(DISTINCT s.activity_id) as unique_activities,
            MIN(s.timestamp) as first_activity,
            MAX(s.timestamp) as last_activity,
            COUNT(r.response) as responses_with_data
        FROM statements_new s
        LEFT JOIN results_new r ON s.statement_id = r.statement_id
        GROUP BY s.source, s.actor_id
        ORDER BY total_activities DESC
        LIMIT 20
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Recent Activity Timeline",
        description="Recent activity from both sources in chronological order",
        sql="""
        SELECT 
            s.source,
            s.actor_id,
            s.activity_id,
            s.verb_id,
            s.timestamp,
            r.response,
            CASE 
                WHEN s.source = 'csv' THEN 
                    (SELECT ce.extension_value FROM context_extensions_new ce 
                     WHERE ce.statement_id = s.statement_id 
                     AND ce.extension_key = 'https://7taps.com/lesson-number' LIMIT 1)
                ELSE 'N/A'
            END as lesson_number
        FROM statements_new s
        LEFT JOIN results_new r ON s.statement_id = r.statement_id
        ORDER BY s.timestamp DESC
        LIMIT 50
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Card Type Distribution",
        description="Distribution of focus group card types (Form, Poll, Quiz, etc.)",
        sql="""
        SELECT 
            ce.extension_value as card_type,
            COUNT(*) as response_count,
            COUNT(DISTINCT s.actor_id) as unique_learners,
            AVG(LENGTH(r.response)) as avg_response_length
        FROM statements_new s
        JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
        LEFT JOIN results_new r ON s.statement_id = r.statement_id
        WHERE s.source = 'csv' 
            AND ce.extension_key = 'https://7taps.com/card-type'
        GROUP BY ce.extension_value
        ORDER BY response_count DESC
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Cross-Source Learner Analysis",
        description="Find learners who appear in both xAPI and CSV data",
        sql="""
        SELECT 
            actor_id,
            COUNT(CASE WHEN source = 'xapi' THEN 1 END) as xapi_activities,
            COUNT(CASE WHEN source = 'csv' THEN 1 END) as csv_responses,
            COUNT(*) as total_activities,
            MIN(timestamp) as first_activity,
            MAX(timestamp) as last_activity
        FROM statements_new
        GROUP BY actor_id
        HAVING COUNT(CASE WHEN source = 'xapi' THEN 1 END) > 0 
           AND COUNT(CASE WHEN source = 'csv' THEN 1 END) > 0
        ORDER BY total_activities DESC
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Response Quality Analysis",
        description="Analyze focus group response quality and engagement",
        sql="""
        SELECT 
            s.actor_id,
            COUNT(*) as total_responses,
            AVG(LENGTH(r.response)) as avg_response_length,
            COUNT(CASE WHEN LENGTH(r.response) > 100 THEN 1 END) as detailed_responses,
            COUNT(CASE WHEN LENGTH(r.response) <= 50 THEN 1 END) as brief_responses,
            ROUND(
                COUNT(CASE WHEN LENGTH(r.response) > 100 THEN 1 END) * 100.0 / COUNT(*), 2
            ) as detailed_response_rate
        FROM statements_new s
        JOIN results_new r ON s.statement_id = r.statement_id
        WHERE s.source = 'csv' AND r.response IS NOT NULL
        GROUP BY s.actor_id
        ORDER BY total_responses DESC
        LIMIT 15
        """,
        category="analytics"
    )
]

async def execute_safe_query(sql: str) -> DBQueryResponse:
    """Execute a safe read-only query via direct database connection"""
    import time
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import os
    
    start_time = time.time()
    
    try:
        # Validate query is read-only
        sql_upper = sql.upper().strip()
        if any(keyword in sql_upper for keyword in ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
        # Get database URL from environment
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise Exception("DATABASE_URL not configured")
        
        # Execute query directly
        with psycopg2.connect(database_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
                results = cursor.fetchall()
                
                # Convert to list of dicts
                result_list = []
                for row in results:
                    result_list.append(dict(row))
                
                execution_time = time.time() - start_time
                
                return DBQueryResponse(
                    query=sql,
                    results=result_list,
                    row_count=len(result_list),
                    execution_time=execution_time
                )
                
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Query execution failed: {e}")
        return DBQueryResponse(
            query=sql,
            results=[],
            row_count=0,
            execution_time=execution_time,
            error=f"Query execution failed: {str(e)}"
        )

@router.get("/ui/db-terminal", response_class=HTMLResponse)
async def db_terminal_page(request: Request):
    """Serve the DB terminal page with embedded SQLPad/Superset"""
    return templates.TemplateResponse(
        "db_terminal.html",
        {
            "request": request,
            "sqlpad_url": admin_config.sqlpad_url,
            "superset_url": admin_config.superset_url,
            "use_sqlpad": admin_config.use_sqlpad,
            "prebuilt_queries": PREBUILT_QUERIES
        }
    )

@router.post("/ui/db-query", response_model=DBQueryResponse)
async def execute_db_query(request: DBQueryRequest):
    """Execute a safe database query"""
    logger.info(f"Executing query: {request.query[:100]}...")
    
    result = await execute_safe_query(request.query)
    return result

@router.get("/ui/prebuilt-queries")
async def get_prebuilt_queries():
    """Get list of prebuilt queries"""
    return {
        "queries": [query.dict() for query in PREBUILT_QUERIES],
        "categories": ["cohort", "completion", "analytics"]
    }

@router.get("/ui/db-status")
async def db_terminal_status():
    """Get DB terminal status and configuration"""
    return {
        "status": "healthy",
        "db_terminal_url": admin_config.get_db_terminal_url(),
        "use_sqlpad": admin_config.use_sqlpad,
        "database_url": admin_config.database_url,
        "prebuilt_queries_count": len(PREBUILT_QUERIES),
        "capabilities": [
            "unified_data_queries",
            "cross_source_analytics", 
            "focus_group_analysis",
            "xapi_activity_patterns",
            "learner_engagement_tracking",
            "response_quality_analysis",
            "real_time_analytics"
        ],
        "data_sources": {
            "csv_focus_group": "373 statements",
            "xapi_real_time": "260 statements",
            "total_unified": "633 statements"
        }
    }

@router.get("/ui/admin")
async def admin_panel():
    """Admin panel overview"""
    return {
        "panel": "7taps Analytics Admin - Unified Data Platform",
        "modules": {
            "db_terminal": "/ui/db-terminal",
            "nlp_query": "/api/ui/nlp-query",
            "etl_status": "/ui/test-etl-streaming",
            "orchestrator": "/api/debug/progress",
            "cohort_analytics": "/api/analytics/cohorts",
            "focus_group_import": "/api/import/focus-group"
        },
        "capabilities": [
            "unified_data_queries",
            "natural_language_queries", 
            "cross_source_analytics",
            "focus_group_analysis",
            "real_time_xapi_tracking",
            "etl_monitoring",
            "progress_tracking"
        ],
        "data_overview": {
            "total_statements": 633,
            "csv_responses": 373,
            "xapi_activities": 260,
            "unique_learners": "15+ focus group + xAPI users",
            "schema": "normalized_relational"
        }
    } 