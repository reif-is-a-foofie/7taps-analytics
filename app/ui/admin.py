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
templates = Jinja2Templates(directory="app/templates")

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
        self.mcp_db_url = os.getenv("MCP_DB_URL", "http://localhost:8080")
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
        name="Cohort Completion Rates",
        description="Show completion rates by cohort",
        sql="""
        SELECT 
            c.cohort_name,
            COUNT(DISTINCT s.actor) as total_users,
            COUNT(DISTINCT CASE WHEN s.verb = 'completed' THEN s.actor END) as completed_users,
            ROUND(
                COUNT(DISTINCT CASE WHEN s.verb = 'completed' THEN s.actor END) * 100.0 / 
                COUNT(DISTINCT s.actor), 2
            ) as completion_rate
        FROM statements s
        LEFT JOIN cohorts c ON s.actor = c.user_id
        WHERE c.cohort_name IS NOT NULL
        GROUP BY c.cohort_name
        ORDER BY completion_rate DESC
        """,
        category="cohort"
    ),
    PrebuiltQuery(
        name="Recent Activity",
        description="Show last 50 statements",
        sql="""
        SELECT 
            actor,
            verb,
            object,
            timestamp
        FROM statements
        ORDER BY timestamp DESC
        LIMIT 50
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="User Engagement",
        description="Top 20 most active users",
        sql="""
        SELECT 
            actor,
            COUNT(*) as statement_count,
            COUNT(DISTINCT DATE(timestamp)) as active_days,
            MAX(timestamp) as last_activity
        FROM statements
        GROUP BY actor
        ORDER BY statement_count DESC
        LIMIT 20
        """,
        category="analytics"
    ),
    PrebuiltQuery(
        name="Completion Trends",
        description="Daily completion rates for last 30 days",
        sql="""
        SELECT 
            DATE_TRUNC('day', timestamp) as date,
            COUNT(DISTINCT actor) as total_users,
            COUNT(DISTINCT CASE WHEN verb = 'completed' THEN actor END) as completed_users,
            ROUND(
                COUNT(DISTINCT CASE WHEN verb = 'completed' THEN actor END) * 100.0 / 
                COUNT(DISTINCT actor), 2
            ) as completion_rate
        FROM statements
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', timestamp)
        ORDER BY date DESC
        """,
        category="completion"
    ),
    PrebuiltQuery(
        name="Verb Distribution",
        description="Most common xAPI verbs",
        sql="""
        SELECT 
            verb,
            COUNT(*) as count,
            COUNT(DISTINCT actor) as unique_users
        FROM statements
        WHERE timestamp >= NOW() - INTERVAL '7 days'
        GROUP BY verb
        ORDER BY count DESC
        """,
        category="analytics"
    )
]

async def execute_safe_query(sql: str) -> DBQueryResponse:
    """Execute a safe read-only query via MCP DB"""
    import time
    start_time = time.time()
    
    try:
        # Validate query is read-only
        sql_upper = sql.upper().strip()
        if any(keyword in sql_upper for keyword in ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
        # Execute via MCP DB
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_config.mcp_db_url}/sql",
                json={"query": sql},
                timeout=30.0
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return DBQueryResponse(
                    query=sql,
                    results=data.get("results", []),
                    row_count=len(data.get("results", [])),
                    execution_time=execution_time
                )
            else:
                return DBQueryResponse(
                    query=sql,
                    results=[],
                    row_count=0,
                    execution_time=execution_time,
                    error=f"MCP DB error: {response.status_code}"
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
        "mcp_db_url": admin_config.mcp_db_url,
        "prebuilt_queries_count": len(PREBUILT_QUERIES),
        "capabilities": [
            "read_only_queries",
            "prebuilt_analytics",
            "cohort_analysis",
            "completion_tracking",
            "user_engagement"
        ]
    }

@router.get("/ui/admin")
async def admin_panel():
    """Admin panel overview"""
    return {
        "panel": "7taps Analytics Admin",
        "modules": {
            "db_terminal": "/ui/db-terminal",
            "nlp_query": "/api/ui/nlp-query",
            "etl_status": "/ui/test-etl-streaming",
            "orchestrator": "/api/debug/progress"
        },
        "capabilities": [
            "database_queries",
            "natural_language_queries",
            "etl_monitoring",
            "progress_tracking"
        ]
    } 