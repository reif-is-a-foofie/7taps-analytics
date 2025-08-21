"""
Analytics API Router - Pre-defined analytics queries for common questions
This router provides standardized analytics endpoints for dashboard and chat integration.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
# Data validation functions - simplified for now
def validate_analytics_result(value, field_name):
    """Simple validation function"""
    if value is None or str(value).lower() in ['false', 'null', 'undefined']:
        return 0
    return value

def validate_analytics_response(data):
    """Simple response validation"""
    return data

router = APIRouter()

# Response Models
class AnalyticsResponse(BaseModel):
    success: bool = Field(..., description="Whether the query was successful")
    chart_type: str = Field(..., description="Type of chart for frontend rendering")
    data: Dict[str, Any] = Field(..., description="Chart data")
    title: str = Field(..., description="Chart title")
    error: Optional[str] = Field(None, description="Error message if query failed")

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(
            os.getenv("DATABASE_URL"),
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Data validation functions are now imported from app.data_validation

def execute_query(sql_query: str, params: tuple = None) -> List[Dict]:
    """Execute a SQL query and return results with validation"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(sql_query, params)
            else:
                cur.execute(sql_query)
            results = cur.fetchall()
            
            # Convert datetime objects to strings for JSON serialization and validate data
            def convert_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                return obj
            
            def clean_dict(d):
                cleaned = {}
                for k, v in d.items():
                    # Validate each value
                    validated_value = validate_analytics_result(v, k)
                    # Convert datetime if needed
                    if hasattr(validated_value, 'isoformat'):
                        cleaned[k] = validated_value.isoformat()
                    else:
                        cleaned[k] = validated_value
                return cleaned
            
            return [clean_dict(dict(row)) for row in results]
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
    finally:
        conn.close()

@router.get("/analytics/completion-rates", 
    response_model=AnalyticsResponse,
    summary="Get completion rates for each lesson",
    description="Returns bar chart data showing completion rates for all lessons"
)
async def get_completion_rates(ranked: bool = Query(False, description="Return ranked results")):
    """Get completion rates for each lesson with optional ranking"""
    try:
        if ranked:
            # Ranked completion rates (highest to lowest)
            sql = """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(10,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                HAVING COUNT(DISTINCT ua.user_id) > 0
                ORDER BY completion_rate DESC
            """
            title = "Lesson Completion Rates (Ranked)"
        else:
            # Standard completion rates by lesson number
            sql = """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(10,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
            title = "Lesson Completion Rates"
        
        results = execute_query(sql)
        
        # Prepare chart data
        labels = [f"Lesson {r['lesson_number']}" for r in results]
        values = [r['completion_rate'] or 0 for r in results]
        colors = ['#6366f1' if v >= 70 else '#f59e0b' if v >= 50 else '#ef4444' for v in values]
        
        return AnalyticsResponse(
            success=True,
            chart_type="bar",
            data={
                "labels": labels,
                "datasets": [{
                    "label": "Completion Rate (%)",
                    "data": values,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 1
                }],
                "raw_data": results
            },
            title=title
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="bar",
            data={},
            title="Completion Rates",
            error=str(e)
        )

@router.get("/analytics/engagement-over-time",
    response_model=AnalyticsResponse,
    summary="Get student engagement over time",
    description="Returns line chart data showing engagement trends over time"
)
async def get_engagement_over_time():
    """Get student engagement over time across the course"""
    try:
        sql = """
            SELECT 
                DATE(ua.timestamp) as activity_date,
                COUNT(DISTINCT ua.user_id) as active_users,
                COUNT(*) as total_activities,
                COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as completions
            FROM user_activities ua
            WHERE ua.timestamp >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(ua.timestamp)
            ORDER BY activity_date
        """
        
        results = execute_query(sql)
        
        # Prepare chart data
        dates = [r['activity_date'] for r in results]
        active_users = [r['active_users'] for r in results]
        total_activities = [r['total_activities'] for r in results]
        completions = [r['completions'] for r in results]
        
        return AnalyticsResponse(
            success=True,
            chart_type="line",
            data={
                "labels": dates,
                "datasets": [
                    {
                        "label": "Active Users",
                        "data": active_users,
                        "borderColor": "#6366f1",
                        "backgroundColor": "rgba(99, 102, 241, 0.1)",
                        "tension": 0.4
                    },
                    {
                        "label": "Total Activities",
                        "data": total_activities,
                        "borderColor": "#10b981",
                        "backgroundColor": "rgba(16, 185, 129, 0.1)",
                        "tension": 0.4
                    },
                    {
                        "label": "Completions",
                        "data": completions,
                        "borderColor": "#f59e0b",
                        "backgroundColor": "rgba(245, 158, 11, 0.1)",
                        "tension": 0.4
                    }
                ],
                "raw_data": results
            },
            title="Student Engagement Over Time"
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="line",
            data={},
            title="Engagement Over Time",
            error=str(e)
        )

@router.get("/analytics/incomplete-students",
    response_model=AnalyticsResponse,
    summary="Get students who haven't finished the course",
    description="Returns table data showing incomplete students and their progress"
)
async def get_incomplete_students():
    """Get students who haven't finished the course yet"""
    try:
        sql = """
            SELECT 
                u.user_id,
                u.cohort,
                COUNT(DISTINCT ua.lesson_id) as lessons_started,
                (SELECT COUNT(*) FROM lessons) as total_lessons,
                (SELECT COUNT(*) FROM lessons) - COUNT(DISTINCT ua.lesson_id) as lessons_remaining,
                CAST(
                    (COUNT(DISTINCT ua.lesson_id)::float / (SELECT COUNT(*) FROM lessons)::float) * 100 AS NUMERIC(10,1)
                ) as progress_percentage
            FROM users u
            LEFT JOIN user_activities ua ON u.id = ua.user_id
            GROUP BY u.id, u.user_id, u.cohort
            HAVING COUNT(DISTINCT ua.lesson_id) < (SELECT COUNT(*) FROM lessons)
            ORDER BY progress_percentage DESC
        """
        
        results = execute_query(sql)
        
        # Prepare table data
        columns = [
            {"field": "user_id", "headerName": "User ID", "width": 150},
            {"field": "cohort", "headerName": "Cohort", "width": 200},
            {"field": "lessons_started", "headerName": "Lessons Started", "width": 150},
            {"field": "total_lessons", "headerName": "Total Lessons", "width": 150},
            {"field": "lessons_remaining", "headerName": "Remaining", "width": 150},
            {"field": "progress_percentage", "headerName": "Progress %", "width": 150}
        ]
        
        return AnalyticsResponse(
            success=True,
            chart_type="table",
            data={
                "columns": columns,
                "rows": results,
                "total_count": len(results)
            },
            title="Incomplete Students"
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="table",
            data={},
            title="Incomplete Students",
            error=str(e)
        )

@router.get("/analytics/average-completion",
    response_model=AnalyticsResponse,
    summary="Get average completion rate across all lessons",
    description="Returns single metric showing overall completion rate"
)
async def get_average_completion():
    """Get average completion rate across all lessons"""
    try:
        sql = """
            SELECT 
                CAST(AVG(completion_rate) AS NUMERIC(10,1)) as average_completion_rate,
                COUNT(*) as total_lessons,
                SUM(users_started) as total_users_started,
                SUM(users_completed) as total_users_completed
            FROM (
                SELECT 
                    l.lesson_number,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(10,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                GROUP BY l.id, l.lesson_number
                HAVING COUNT(DISTINCT ua.user_id) > 0
            ) as lesson_stats
        """
        
        results = execute_query(sql)
        result = results[0] if results else {}
        
        avg_rate = result.get('average_completion_rate', 0) or 0
        
        return AnalyticsResponse(
            success=True,
            chart_type="metric",
            data={
                "value": avg_rate,
                "label": "Average Completion Rate",
                "unit": "%",
                "color": "#6366f1" if avg_rate >= 70 else "#f59e0b" if avg_rate >= 50 else "#ef4444",
                "details": {
                    "total_lessons": result.get('total_lessons', 0),
                    "total_users_started": result.get('total_users_started', 0),
                    "total_users_completed": result.get('total_users_completed', 0)
                }
            },
            title="Average Completion Rate"
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="metric",
            data={},
            title="Average Completion Rate",
            error=str(e)
        )

@router.get("/analytics/lesson-comparison",
    response_model=AnalyticsResponse,
    summary="Compare completion rates between two lessons",
    description="Returns comparison chart data for two specific lessons"
)
async def get_lesson_comparison(
    lesson1: int = Query(..., description="First lesson number"),
    lesson2: int = Query(..., description="Second lesson number")
):
    """Compare completion rates between two specific lessons"""
    try:
        sql = """
            SELECT 
                l.lesson_number,
                l.lesson_name,
                COUNT(DISTINCT ua.user_id) as users_started,
                COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                CAST(
                    (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                     NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(10,1)
                ) as completion_rate
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            WHERE l.lesson_number = %s OR l.lesson_number = %s
            GROUP BY l.id, l.lesson_number, l.lesson_name
            ORDER BY l.lesson_number
        """
        
        results = execute_query(sql, (lesson1, lesson2))
        
        # Prepare comparison data
        labels = [f"Lesson {r['lesson_number']}" for r in results]
        completion_rates = [r['completion_rate'] or 0 for r in results]
        users_started = [r['users_started'] for r in results]
        users_completed = [r['users_completed'] for r in results]
        
        return AnalyticsResponse(
            success=True,
            chart_type="comparison",
            data={
                "labels": labels,
                "datasets": [
                    {
                        "label": "Completion Rate (%)",
                        "data": completion_rates,
                        "backgroundColor": ["#6366f1", "#10b981"],
                        "borderColor": ["#6366f1", "#10b981"],
                        "borderWidth": 2
                    }
                ],
                "comparison": {
                    "lesson1": {
                        "number": lesson1,
                        "completion_rate": completion_rates[0] if len(completion_rates) > 0 else 0,
                        "users_started": users_started[0] if len(users_started) > 0 else 0,
                        "users_completed": users_completed[0] if len(users_completed) > 0 else 0
                    },
                    "lesson2": {
                        "number": lesson2,
                        "completion_rate": completion_rates[1] if len(completion_rates) > 1 else 0,
                        "users_started": users_started[1] if len(users_started) > 1 else 0,
                        "users_completed": users_completed[1] if len(users_completed) > 1 else 0
                    }
                },
                "raw_data": results
            },
            title=f"Lesson {lesson1} vs Lesson {lesson2} Comparison"
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="comparison",
            data={},
            title="Lesson Comparison",
            error=str(e)
        )

@router.get("/analytics/completion-speed",
    response_model=AnalyticsResponse,
    summary="Get completion speed analysis",
    description="Returns histogram data showing how quickly students complete the course"
)
async def get_completion_speed(days: int = Query(30, description="Number of days to analyze")):
    """Get completion speed analysis - how many students completed within specified days"""
    try:
        sql = """
            SELECT 
                u.user_id,
                u.cohort,
                MIN(ua.timestamp) as first_activity,
                MAX(ua.timestamp) as last_activity,
                EXTRACT(DAYS FROM MAX(ua.timestamp) - MIN(ua.timestamp)) as days_to_complete,
                COUNT(DISTINCT ua.lesson_id) as lessons_completed
            FROM users u
            JOIN user_activities ua ON u.id = ua.user_id
            GROUP BY u.id, u.user_id, u.cohort
            HAVING COUNT(DISTINCT ua.lesson_id) >= (SELECT COUNT(*) FROM lessons) * 0.8
            ORDER BY days_to_complete
        """
        
        results = execute_query(sql)
        
        # Analyze completion speed
        completed_within_days = [r for r in results if r['days_to_complete'] <= days]
        total_completers = len(results)
        completed_within_target = len(completed_within_days)
        
        # Create histogram data
        speed_ranges = [
            {"range": "0-7 days", "count": 0},
            {"range": "8-14 days", "count": 0},
            {"range": "15-30 days", "count": 0},
            {"range": "31-60 days", "count": 0},
            {"range": "60+ days", "count": 0}
        ]
        
        for result in results:
            days_to_complete = result['days_to_complete'] or 0
            if days_to_complete <= 7:
                speed_ranges[0]["count"] += 1
            elif days_to_complete <= 14:
                speed_ranges[1]["count"] += 1
            elif days_to_complete <= 30:
                speed_ranges[2]["count"] += 1
            elif days_to_complete <= 60:
                speed_ranges[3]["count"] += 1
            else:
                speed_ranges[4]["count"] += 1
        
        return AnalyticsResponse(
            success=True,
            chart_type="histogram",
            data={
                "labels": [r["range"] for r in speed_ranges],
                "datasets": [{
                    "label": "Number of Students",
                    "data": [r["count"] for r in speed_ranges],
                    "backgroundColor": "#6366f1",
                    "borderColor": "#6366f1",
                    "borderWidth": 1
                }],
                "summary": {
                    "total_completers": total_completers,
                    "completed_within_target_days": completed_within_target,
                    "target_days": days,
                    "percentage_within_target": round((completed_within_target / total_completers * 100) if total_completers > 0 else 0, 1)
                },
                "raw_data": results
            },
            title=f"Completion Speed Analysis ({days} days target)"
        )
        
    except Exception as e:
        return AnalyticsResponse(
            success=False,
            chart_type="histogram",
            data={},
            title="Completion Speed",
            error=str(e)
        )

@router.get("/analytics/health", summary="Analytics API health check")
async def analytics_health():
    """Health check for analytics API"""
    return {
        "status": "healthy",
        "service": "analytics-api",
        "endpoints": [
            "/api/analytics/completion-rates",
            "/api/analytics/engagement-over-time",
            "/api/analytics/incomplete-students", 
            "/api/analytics/average-completion",
            "/api/analytics/lesson-comparison",
            "/api/analytics/completion-speed"
        ]
    }
