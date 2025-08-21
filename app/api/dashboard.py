"""
Analytics Dashboard API for 7taps Analytics.

This module provides API endpoints for the Analytics Dashboard sub-app
with standard contract actions: load_dashboard, get_metrics, get_charts.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from app.data_validation import (
    validate_database_value, 
    validate_chart_dataset, 
    validate_metrics_data, 
    validate_summary_data,
    check_for_false_indicators
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class DashboardResponse(BaseModel):
    """Standard response model for dashboard actions."""
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: datetime

class MetricsRequest(BaseModel):
    """Request model for metrics endpoint."""
    metric_type: Optional[str] = None

class ChartsRequest(BaseModel):
    """Request model for charts endpoint."""
    chart_type: Optional[str] = None

def validate_database_connection():
    """Validate database connection and return connection object."""
    try:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))
        
        # Test the connection
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return conn
    except Exception as e:
        logger.error(f"Database connection validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Data validation functions are now imported from app.data_validation

def get_db_connection():
    """Get database connection with proper error handling."""
    return validate_database_connection()

@router.get("/dashboard/load", response_model=DashboardResponse)
async def load_dashboard():
    """
    AnalyticsDashboard.load_dashboard action
    
    Returns comprehensive dashboard data including charts, metrics, and summary.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get basic metrics with validation
        cursor.execute("SELECT COUNT(DISTINCT id) as total_users FROM users")
        total_users = validate_database_value(cursor.fetchone()['total_users'], 'total_users', 'int')
        
        cursor.execute("SELECT COUNT(DISTINCT id) as total_activities FROM user_activities")
        total_activities = validate_database_value(cursor.fetchone()['total_activities'], 'total_activities', 'int')
        
        cursor.execute("SELECT COUNT(DISTINCT id) as total_responses FROM user_responses")
        total_responses = validate_database_value(cursor.fetchone()['total_responses'], 'total_responses', 'int')
        
        cursor.execute("SELECT COUNT(DISTINCT id) as total_questions FROM questions")
        total_questions = validate_database_value(cursor.fetchone()['total_questions'], 'total_questions', 'int')
        
        # Get lesson completion data for charts with validation
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
        lesson_completion_data = validate_chart_dataset(lesson_completion_data, 'lesson_completion')
        
        # Get problematic users with lowest completion rates
        cursor.execute("""
            SELECT 
                u.user_id,
                COALESCE(u.cohort, 'Unknown') as user_info,
                COUNT(DISTINCT ua.lesson_id) as lessons_started,
                COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.lesson_id END) as lessons_completed,
                CAST(
                    (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.lesson_id END)::float / 
                     NULLIF(COUNT(DISTINCT ua.lesson_id), 0) * 100) AS NUMERIC(5,1)
                ) as completion_rate,
                COUNT(ua.id) as total_activities
            FROM users u
            LEFT JOIN user_activities ua ON u.id = ua.user_id
            WHERE ua.lesson_id IS NOT NULL
            GROUP BY u.id, u.user_id, u.cohort
            HAVING COUNT(DISTINCT ua.lesson_id) > 0
            ORDER BY completion_rate ASC, total_activities ASC
            LIMIT 10
        """)
        problematic_users_data = cursor.fetchall()
        problematic_users_data = validate_chart_dataset(problematic_users_data, 'problematic_users')
        
        cursor.close()
        conn.close()
        
        # Prepare charts data with validation
        charts = []
        
        if lesson_completion_data:
            charts.append({
                "type": "lesson_completion",
                "title": "Lesson Completion Rates",
                "data": [
                    {
                        "lesson": validate_database_value(row['lesson_name'], 'lesson_name', 'str'),
                        "started": validate_database_value(row['users_started'], 'users_started', 'int'),
                        "completed": validate_database_value(row['users_completed'], 'users_completed', 'int'),
                        "rate": validate_database_value(row['completion_rate'], 'completion_rate', 'float')
                    }
                    for row in lesson_completion_data
                ]
            })
        
        if problematic_users_data:
            charts.append({
                "type": "problematic_users",
                "title": "Problematic Users - Lowest Completion Rates",
                "data": [
                    {
                        "user": validate_database_value(row['user_id'], 'user_id', 'str'),
                        "user_info": validate_database_value(row['user_info'], 'user_info', 'str'),
                        "lessons_started": validate_database_value(row['lessons_started'], 'lessons_started', 'int'),
                        "lessons_completed": validate_database_value(row['lessons_completed'], 'lessons_completed', 'int'),
                        "rate": validate_database_value(row['completion_rate'], 'completion_rate', 'float'),
                        "activities": validate_database_value(row['total_activities'], 'total_activities', 'int')
                    }
                    for row in problematic_users_data
                ]
            })
        

        
        # Prepare metrics data with validation
        metrics = [
            {
                "name": "Total Users",
                "value": total_users,
                "type": "count",
                "trend": "up"
            },
            {
                "name": "Total Activities",
                "value": total_activities,
                "type": "count",
                "trend": "up"
            },
            {
                "name": "Total Responses",
                "value": total_responses,
                "type": "count",
                "trend": "up"
            },
            {
                "name": "Total Questions",
                "value": total_questions,
                "type": "count",
                "trend": "stable"
            }
        ]
        
        # Prepare summary with validation
        avg_completion_rate = 0.0
        if lesson_completion_data:
            completion_rates = [validate_database_value(row['completion_rate'], 'completion_rate', 'float') for row in lesson_completion_data]
            avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0.0
        
        summary = {
            "total_lessons": len(lesson_completion_data),
            "avg_completion_rate": avg_completion_rate,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return DashboardResponse(
            success=True,
            data={
                "charts": charts,
                "metrics": metrics,
                "summary": summary
            },
            message="Dashboard loaded successfully with validated data",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return DashboardResponse(
            success=False,
            data={},
            message=f"Failed to load dashboard: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.post("/dashboard/metrics", response_model=DashboardResponse)
async def get_metrics(request: MetricsRequest):
    """
    AnalyticsDashboard.get_metrics action
    
    Returns specific metrics based on metric_type.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        metrics = []
        
        if not request.metric_type or request.metric_type == "all":
            # Get all metrics
            cursor.execute("SELECT COUNT(DISTINCT id) as total_users FROM users")
            total_users = validate_database_value(cursor.fetchone()['total_users'], 'total_users', 'int')
            
            cursor.execute("SELECT COUNT(DISTINCT id) as total_activities FROM user_activities")
            total_activities = validate_database_value(cursor.fetchone()['total_activities'], 'total_activities', 'int')
            
            cursor.execute("SELECT COUNT(DISTINCT id) as total_responses FROM user_responses")
            total_responses = validate_database_value(cursor.fetchone()['total_responses'], 'total_responses', 'int')
            
            cursor.execute("SELECT COUNT(DISTINCT id) as total_questions FROM questions")
            total_questions = validate_database_value(cursor.fetchone()['total_questions'], 'total_questions', 'int')
            
            metrics = [
                {
                    "name": "Total Users",
                    "value": total_users,
                    "type": "count"
                },
                {
                    "name": "Total Activities", 
                    "value": total_activities,
                    "type": "count"
                },
                {
                    "name": "Total Responses",
                    "value": total_responses,
                    "type": "count"
                },
                {
                    "name": "Total Questions",
                    "value": total_questions,
                    "type": "count"
                }
            ]
        elif request.metric_type == "users":
            cursor.execute("SELECT COUNT(DISTINCT id) as total_users FROM users")
            total_users = validate_database_value(cursor.fetchone()['total_users'], 'total_users', 'int')
            metrics = [{"name": "Total Users", "value": total_users, "type": "count"}]
        elif request.metric_type == "activities":
            cursor.execute("SELECT COUNT(DISTINCT id) as total_activities FROM user_activities")
            total_activities = validate_database_value(cursor.fetchone()['total_activities'], 'total_activities', 'int')
            metrics = [{"name": "Total Activities", "value": total_activities, "type": "count"}]
        elif request.metric_type == "responses":
            cursor.execute("SELECT COUNT(DISTINCT id) as total_responses FROM user_responses")
            total_responses = validate_database_value(cursor.fetchone()['total_responses'], 'total_responses', 'int')
            metrics = [{"name": "Total Responses", "value": total_responses, "type": "count"}]
        else:
            raise HTTPException(status_code=400, detail=f"Unknown metric type: {request.metric_type}")
        
        cursor.close()
        conn.close()
        
        return DashboardResponse(
            success=True,
            data={"metrics": metrics},
            message=f"Metrics retrieved successfully for type: {request.metric_type or 'all'}",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return DashboardResponse(
            success=False,
            data={},
            message=f"Failed to get metrics: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.post("/dashboard/charts", response_model=DashboardResponse)
async def get_charts(request: ChartsRequest):
    """
    AnalyticsDashboard.get_charts action
    
    Returns specific charts based on chart_type.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        charts = []
        
        if not request.chart_type or request.chart_type == "all":
            # Get all charts
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
            lesson_completion_data = validate_chart_dataset(lesson_completion_data, 'lesson_completion')
            
            charts = [
                {
                    "type": "lesson_completion",
                    "title": "Lesson Completion Rates",
                    "data": [
                        {
                            "lesson": validate_database_value(row['lesson_name'], 'lesson_name', 'str'),
                            "started": validate_database_value(row['users_started'], 'users_started', 'int'),
                            "completed": validate_database_value(row['users_completed'], 'users_completed', 'int'),
                            "rate": validate_database_value(row['completion_rate'], 'completion_rate', 'float')
                        }
                        for row in lesson_completion_data
                    ]
                }
            ]
        elif request.chart_type == "lesson_completion":
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
            lesson_completion_data = validate_chart_dataset(lesson_completion_data, 'lesson_completion')
            
            charts = [{
                "type": "lesson_completion",
                "title": "Lesson Completion Rates",
                "data": [
                    {
                        "lesson": validate_database_value(row['lesson_name'], 'lesson_name', 'str'),
                        "started": validate_database_value(row['users_started'], 'users_started', 'int'),
                        "completed": validate_database_value(row['users_completed'], 'users_completed', 'int'),
                        "rate": validate_database_value(row['completion_rate'], 'completion_rate', 'float')
                    }
                    for row in lesson_completion_data
                ]
            }]

        else:
            raise HTTPException(status_code=400, detail=f"Unknown chart type: {request.chart_type}")
        
        cursor.close()
        conn.close()
        
        return DashboardResponse(
            success=True,
            data={"charts": charts},
            message=f"Charts retrieved successfully for type: {request.chart_type or 'all'}",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting charts: {e}")
        return DashboardResponse(
            success=False,
            data={},
            message=f"Failed to get charts: {str(e)}",
            timestamp=datetime.utcnow()
        )
