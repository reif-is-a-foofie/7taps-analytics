"""
Public Data API - External-facing endpoints for data consumers
This module provides clean, validated data access for external consumers.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from app.data_validation import validate_database_value, validate_chart_dataset, sanitize_for_json

router = APIRouter(prefix="/api/public", tags=["Public Data API"])

# Response Models
class PublicDataResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    data: Dict[str, Any] = Field(..., description="The requested data")
    metadata: Dict[str, Any] = Field(..., description="Metadata about the response")
    timestamp: datetime = Field(..., description="When the data was generated")

class QueryRequest(BaseModel):
    query_type: str = Field(..., description="Type of query to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Query parameters")

def get_db_connection():
    """Get database connection with validation"""
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
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def execute_safe_query(sql: str, params: tuple = None) -> List[Dict]:
    """Execute a safe query and return validated results"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            results = cur.fetchall()
            
            # Validate and sanitize results
            validated_results = []
            for row in results:
                validated_row = {}
                for key, value in row.items():
                    validated_value = validate_database_value(value, f"public.{key}")
                    validated_row[key] = validated_value
                validated_results.append(validated_row)
            
            return validated_results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")
    finally:
        conn.close()

@router.get("/metrics/overview", response_model=PublicDataResponse)
async def get_metrics_overview():
    """
    Get overview metrics for the learning platform.
    
    Returns key metrics including user counts, activity levels, and engagement statistics.
    """
    try:
        # Get total users
        users_query = "SELECT COUNT(DISTINCT id) as total_users FROM users"
        total_users = execute_safe_query(users_query)[0]['total_users']
        
        # Get total activities
        activities_query = "SELECT COUNT(DISTINCT id) as total_activities FROM user_activities"
        total_activities = execute_safe_query(activities_query)[0]['total_activities']
        
        # Get total responses
        responses_query = "SELECT COUNT(DISTINCT id) as total_responses FROM user_responses"
        total_responses = execute_safe_query(responses_query)[0]['total_responses']
        
        # Get total questions
        questions_query = "SELECT COUNT(DISTINCT id) as total_questions FROM questions"
        total_questions = execute_safe_query(questions_query)[0]['total_questions']
        
        # Get recent activity (last 7 days)
        recent_query = """
            SELECT COUNT(*) as recent_activities
            FROM user_activities 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """
        recent_activities = execute_safe_query(recent_query)[0]['recent_activities']
        
        # Get average completion rate
        completion_query = """
            SELECT 
                ROUND(AVG(completion_rate), 1) as avg_completion_rate
            FROM (
                SELECT 
                    l.lesson_number,
                    ROUND(
                        (COUNT(DISTINCT ur.user_id)::float / NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100)::numeric, 1
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                LEFT JOIN user_responses ur ON l.lesson_number = ur.lesson_number
                GROUP BY l.id, l.lesson_number
                HAVING COUNT(DISTINCT ua.user_id) > 0
            ) lesson_stats
        """
        avg_completion = execute_safe_query(completion_query)[0]['avg_completion_rate']
        
        data = {
            "total_users": total_users,
            "total_activities": total_activities,
            "total_responses": total_responses,
            "total_questions": total_questions,
            "recent_activities_7_days": recent_activities,
            "average_completion_rate": avg_completion,
            "platform_health": "active" if total_users > 0 else "inactive"
        }
        
        return PublicDataResponse(
            success=True,
            data=data,
            metadata={
                "description": "Overview metrics for the learning platform",
                "data_source": "users, user_activities, user_responses, questions tables",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "5 minutes"
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics overview: {str(e)}")

@router.get("/analytics/lesson-completion", response_model=PublicDataResponse)
async def get_lesson_completion_analytics():
    """
    Get lesson completion analytics with real data.
    
    Returns completion rates, user engagement, and progress statistics for each lesson.
    """
    try:
        # Get lesson completion data
        completion_query = """
            SELECT 
                l.lesson_number,
                l.lesson_name,
                COUNT(DISTINCT ua.user_id) as users_started,
                COUNT(DISTINCT ur.user_id) as users_completed,
                ROUND(
                    (COUNT(DISTINCT ur.user_id)::float / NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100)::numeric, 1
                ) as completion_rate,
                COUNT(*) as total_interactions
            FROM lessons l
            LEFT JOIN user_activities ua ON l.id = ua.lesson_id
            LEFT JOIN user_responses ur ON l.lesson_number = ur.lesson_number
            GROUP BY l.id, l.lesson_name, l.lesson_number
            ORDER BY l.lesson_number
        """
        
        lesson_data = execute_safe_query(completion_query)
        
        # Calculate summary statistics
        total_lessons = len(lesson_data)
        total_started = sum(lesson['users_started'] for lesson in lesson_data)
        total_completed = sum(lesson['users_completed'] for lesson in lesson_data)
        avg_completion_rate = sum(lesson['completion_rate'] for lesson in lesson_data) / total_lessons if total_lessons > 0 else 0
        
        # Find best and worst performing lessons
        if lesson_data:
            best_lesson = max(lesson_data, key=lambda x: x['completion_rate'])
            worst_lesson = min(lesson_data, key=lambda x: x['completion_rate'])
        else:
            best_lesson = worst_lesson = None
        
        data = {
            "lessons": lesson_data,
            "summary": {
                "total_lessons": total_lessons,
                "total_users_started": total_started,
                "total_users_completed": total_completed,
                "average_completion_rate": round(avg_completion_rate, 1),
                "best_performing_lesson": best_lesson,
                "worst_performing_lesson": worst_lesson
            }
        }
        
        return PublicDataResponse(
            success=True,
            data=data,
            metadata={
                "description": "Lesson completion analytics with detailed statistics",
                "data_source": "lessons, user_activities, user_responses tables",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "10 minutes"
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lesson completion analytics: {str(e)}")

@router.get("/analytics/user-engagement", response_model=PublicDataResponse)
async def get_user_engagement_analytics():
    """
    Get user engagement analytics with real data.
    
    Returns user activity patterns, engagement levels, and participation statistics.
    """
    try:
        # Get user engagement data
        engagement_query = """
            SELECT 
                ua.user_id,
                COUNT(*) as total_activities,
                COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
                MIN(ua.created_at) as first_activity,
                MAX(ua.created_at) as last_activity,
                ROUND(
                    EXTRACT(EPOCH FROM (MAX(ua.created_at) - MIN(ua.created_at))) / 3600, 1
                ) as hours_engaged
            FROM user_activities ua
            GROUP BY ua.user_id
            ORDER BY total_activities DESC
        """
        
        user_data = execute_safe_query(engagement_query)
        
        # Calculate engagement statistics
        total_users = len(user_data)
        total_activities = sum(user['total_activities'] for user in user_data)
        avg_activities_per_user = total_activities / total_users if total_users > 0 else 0
        
        # Categorize users by engagement level
        engagement_categories = {
            "high": len([u for u in user_data if u['total_activities'] >= 20]),
            "medium": len([u for u in user_data if 5 <= u['total_activities'] < 20]),
            "low": len([u for u in user_data if u['total_activities'] < 5])
        }
        
        # Get recent activity trends
        recent_trends_query = """
            SELECT 
                DATE(ua.created_at) as activity_date,
                COUNT(*) as activities,
                COUNT(DISTINCT ua.user_id) as active_users
            FROM user_activities ua
            WHERE ua.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(ua.created_at)
            ORDER BY activity_date
        """
        
        activity_trends = execute_safe_query(recent_trends_query)
        
        data = {
            "user_engagement": user_data,
            "engagement_summary": {
                "total_users": total_users,
                "total_activities": total_activities,
                "average_activities_per_user": round(avg_activities_per_user, 1),
                "engagement_categories": engagement_categories
            },
            "activity_trends": activity_trends
        }
        
        return PublicDataResponse(
            success=True,
            data=data,
            metadata={
                "description": "User engagement analytics with activity patterns",
                "data_source": "user_activities table",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "15 minutes"
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user engagement analytics: {str(e)}")

@router.get("/data/sample", response_model=PublicDataResponse)
async def get_sample_data():
    """
    Get sample data for testing and development.
    
    Returns a small sample of real data from various tables for API testing.
    """
    try:
        # Get sample users
        users_query = "SELECT id, user_id, cohort FROM users LIMIT 5"
        sample_users = execute_safe_query(users_query)
        
        # Get sample activities
        activities_query = """
            SELECT ua.id, ua.user_id, ua.lesson_id, ua.activity_type, ua.created_at
            FROM user_activities ua
            ORDER BY ua.created_at DESC
            LIMIT 10
        """
        sample_activities = execute_safe_query(activities_query)
        
        # Get sample responses
        responses_query = """
            SELECT ur.id, ur.user_id, ur.question_id, ur.response, ur.created_at
            FROM user_responses ur
            ORDER BY ur.created_at DESC
            LIMIT 10
        """
        sample_responses = execute_safe_query(responses_query)
        
        # Get sample lessons
        lessons_query = "SELECT id, lesson_name, lesson_number FROM lessons LIMIT 5"
        sample_lessons = execute_safe_query(lessons_query)
        
        data = {
            "sample_users": sample_users,
            "sample_activities": sample_activities,
            "sample_responses": sample_responses,
            "sample_lessons": sample_lessons,
            "data_quality": {
                "total_records": len(sample_users) + len(sample_activities) + len(sample_responses) + len(sample_lessons),
                "validation_status": "validated",
                "false_indicators_removed": True
            }
        }
        
        return PublicDataResponse(
            success=True,
            data=data,
            metadata={
                "description": "Sample data for API testing and development",
                "data_source": "users, user_activities, user_responses, lessons tables",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "1 hour",
                "note": "This is a small sample of real data for testing purposes"
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sample data: {str(e)}")

@router.get("/health", response_model=PublicDataResponse)
async def get_public_health():
    """
    Get public API health status with data validation information.
    """
    try:
        # Test database connection
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
        conn.close()
        
        data = {
            "status": "healthy",
            "database_connected": True,
            "tables_available": table_count,
            "data_validation": "enabled",
            "api_version": "1.0.0"
        }
        
        return PublicDataResponse(
            success=True,
            data=data,
            metadata={
                "description": "Public API health status",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "1 minute"
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        data = {
            "status": "unhealthy",
            "database_connected": False,
            "error": str(e),
            "data_validation": "enabled",
            "api_version": "1.0.0"
        }
        
        return PublicDataResponse(
            success=False,
            data=data,
            metadata={
                "description": "Public API health status - database connection failed",
                "last_updated": datetime.utcnow().isoformat(),
                "refresh_interval": "1 minute"
            },
            timestamp=datetime.utcnow()
        )
