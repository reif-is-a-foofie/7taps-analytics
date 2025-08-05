from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import httpx
import os
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Templates setup
templates = Jinja2Templates(directory="app/templates")

class DashboardMetrics(BaseModel):
    total_users: int
    total_statements: int
    completion_rate: float
    active_users_7d: int
    active_users_30d: int
    top_verbs: List[Dict[str, Any]]
    cohort_completion: List[Dict[str, Any]]
    daily_activity: List[Dict[str, Any]]

class DashboardConfig:
    def __init__(self):
        self.mcp_db_url = os.getenv("MCP_DB_URL", "http://localhost:8080")
        self.refresh_interval = int(os.getenv("DASHBOARD_REFRESH_INTERVAL", "300"))  # 5 minutes
        
    def get_metrics_query(self, metric_type: str) -> str:
        """Get SQL query for specific metric type"""
        queries = {
            "total_users": """
                SELECT COUNT(DISTINCT actor) as total_users
                FROM statements
            """,
            "total_statements": """
                SELECT COUNT(*) as total_statements
                FROM statements
            """,
            "completion_rate": """
                SELECT 
                    ROUND(
                        COUNT(DISTINCT CASE WHEN verb = 'completed' THEN actor END) * 100.0 / 
                        COUNT(DISTINCT actor), 2
                    ) as completion_rate
                FROM statements
            """,
            "active_users_7d": """
                SELECT COUNT(DISTINCT actor) as active_users_7d
                FROM statements
                WHERE timestamp >= NOW() - INTERVAL '7 days'
            """,
            "active_users_30d": """
                SELECT COUNT(DISTINCT actor) as active_users_30d
                FROM statements
                WHERE timestamp >= NOW() - INTERVAL '30 days'
            """,
            "top_verbs": """
                SELECT 
                    verb,
                    COUNT(*) as count,
                    COUNT(DISTINCT actor) as unique_users
                FROM statements
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY verb
                ORDER BY count DESC
                LIMIT 10
            """,
            "cohort_completion": """
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
            "daily_activity": """
                SELECT 
                    DATE_TRUNC('day', timestamp) as date,
                    COUNT(DISTINCT actor) as active_users,
                    COUNT(*) as total_statements
                FROM statements
                WHERE timestamp >= NOW() - INTERVAL '30 days'
                GROUP BY DATE_TRUNC('day', timestamp)
                ORDER BY date DESC
            """
        }
        return queries.get(metric_type, "")

# Initialize config
dashboard_config = DashboardConfig()

async def execute_metrics_query(sql: str) -> List[Dict[str, Any]]:
    """Execute metrics query via MCP DB"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{dashboard_config.mcp_db_url}/sql",
                json={"query": sql},
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.error(f"MCP DB error: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Metrics query failed: {e}")
        return []

async def get_dashboard_metrics() -> DashboardMetrics:
    """Get comprehensive dashboard metrics"""
    try:
        # Get basic metrics
        total_users_result = await execute_metrics_query(dashboard_config.get_metrics_query("total_users"))
        total_statements_result = await execute_metrics_query(dashboard_config.get_metrics_query("total_statements"))
        completion_rate_result = await execute_metrics_query(dashboard_config.get_metrics_query("completion_rate"))
        active_users_7d_result = await execute_metrics_query(dashboard_config.get_metrics_query("active_users_7d"))
        active_users_30d_result = await execute_metrics_query(dashboard_config.get_metrics_query("active_users_30d"))
        
        # Get detailed metrics
        top_verbs_result = await execute_metrics_query(dashboard_config.get_metrics_query("top_verbs"))
        cohort_completion_result = await execute_metrics_query(dashboard_config.get_metrics_query("cohort_completion"))
        daily_activity_result = await execute_metrics_query(dashboard_config.get_metrics_query("daily_activity"))
        
        return DashboardMetrics(
            total_users=total_users_result[0].get("total_users", 0) if total_users_result else 0,
            total_statements=total_statements_result[0].get("total_statements", 0) if total_statements_result else 0,
            completion_rate=completion_rate_result[0].get("completion_rate", 0.0) if completion_rate_result else 0.0,
            active_users_7d=active_users_7d_result[0].get("active_users_7d", 0) if active_users_7d_result else 0,
            active_users_30d=active_users_30d_result[0].get("active_users_30d", 0) if active_users_30d_result else 0,
            top_verbs=top_verbs_result,
            cohort_completion=cohort_completion_result,
            daily_activity=daily_activity_result
        )
        
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        # Return default metrics if database is not available
        return DashboardMetrics(
            total_users=0,
            total_statements=0,
            completion_rate=0.0,
            active_users_7d=0,
            active_users_30d=0,
            top_verbs=[],
            cohort_completion=[],
            daily_activity=[]
        )

@router.get("/ui/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the analytics dashboard page"""
    metrics = await get_dashboard_metrics()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "metrics": metrics,
            "refresh_interval": dashboard_config.refresh_interval,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )

@router.get("/api/dashboard/metrics")
async def get_metrics():
    """Get dashboard metrics as JSON API"""
    metrics = await get_dashboard_metrics()
    return {
        "metrics": metrics.dict(),
        "last_updated": datetime.now().isoformat(),
        "refresh_interval": dashboard_config.refresh_interval
    }

@router.get("/api/dashboard/metrics/{metric_type}")
async def get_specific_metric(metric_type: str):
    """Get specific metric type"""
    sql = dashboard_config.get_metrics_query(metric_type)
    if not sql:
        raise HTTPException(status_code=400, detail=f"Unknown metric type: {metric_type}")
    
    results = await execute_metrics_query(sql)
    return {
        "metric_type": metric_type,
        "results": results,
        "last_updated": datetime.now().isoformat()
    }

@router.get("/api/dashboard/status")
async def dashboard_status():
    """Get dashboard status and configuration"""
    return {
        "status": "healthy",
        "mcp_db_url": dashboard_config.mcp_db_url,
        "refresh_interval": dashboard_config.refresh_interval,
        "available_metrics": [
            "total_users",
            "total_statements", 
            "completion_rate",
            "active_users_7d",
            "active_users_30d",
            "top_verbs",
            "cohort_completion",
            "daily_activity"
        ],
        "capabilities": [
            "real_time_metrics",
            "cohort_analytics",
            "user_engagement",
            "completion_tracking",
            "activity_visualization"
        ]
    } 