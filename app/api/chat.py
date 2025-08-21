from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import openai
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from app.security import get_openai_client, secrets_manager, log_security_event

router = APIRouter()

# Composable Sub-App Contract Models
class AIChatActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: ask_question, analyze_data, generate_chart")
    query: Optional[str] = Field(None, description="Question or query for ask_question action")
    data: Optional[Dict[str, Any]] = Field(None, description="Data for analyze_data or generate_chart actions")
    analysis_type: Optional[str] = Field(None, description="Type of analysis for analyze_data action")
    chart_type: Optional[str] = Field(None, description="Type of chart for generate_chart action")

class AIChatActionResponse(BaseModel):
    success: bool = Field(..., description="Whether the action was successful")
    action: str = Field(..., description="The action that was performed")
    text: Optional[str] = Field(None, description="Text response for ask_question action")
    chart: Optional[Dict[str, Any]] = Field(None, description="Chart data for generate_chart action")
    table: Optional[Dict[str, Any]] = Field(None, description="Table data for ask_question action")
    confidence: Optional[float] = Field(None, description="Confidence score for ask_question action")
    insights: Optional[List[str]] = Field(None, description="Insights for analyze_data action")
    summary: Optional[str] = Field(None, description="Summary for analyze_data action")
    recommendations: Optional[List[str]] = Field(None, description="Recommendations for analyze_data action")
    config: Optional[Dict[str, Any]] = Field(None, description="Chart configuration for generate_chart action")
    error: Optional[str] = Field(None, description="Error message if action failed")

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the message sender", example="user")
    content: str = Field(..., description="Content of the message", example="How many users completed the course?")

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's message to the AI assistant", example="How many users completed the course?")
    history: List[ChatMessage] = Field(default=[], description="Previous conversation history", example=[])

class ChatResponse(BaseModel):
    response: str
    visualization: Optional[str] = None

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

def get_database_schema():
    """Get complete database schema for context"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get table information
            cur.execute("""
                SELECT 
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name IN ('lessons', 'users', 'questions', 'user_activities', 'user_responses')
                ORDER BY table_name, ordinal_position
            """)
            
            schema = {}
            for row in cur.fetchall():
                table_name = row['table_name']
                if table_name not in schema:
                    schema[table_name] = []
                
                schema[table_name].append({
                    'column': row['column_name'],
                    'type': row['data_type'],
                    'nullable': row['is_nullable'] == 'YES',
                    'default': row['column_default']
                })
            
            return schema
    finally:
        conn.close()

def get_preloaded_queries():
    """Get preloaded SQL queries for common analytics"""
    return {
        "engagement_dropoff": {
            "description": "📉 Engagement Drop-Off - Lesson completion funnel",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    COUNT(DISTINCT ur.user_id) as users_engaged,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as completion_rate,
                    CAST(
                        (COUNT(DISTINCT ur.user_id)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as engagement_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "problematic_users": {
            "description": "🚨 Problematic Users - Learners with low completion or engagement",
            "sql": """
                SELECT 
                    u.user_id,
                    COUNT(DISTINCT ua.lesson_id) as lessons_accessed,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.lesson_id END) as lessons_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.lesson_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.lesson_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as completion_percentage,
                    COUNT(ur.id) as total_responses
                FROM users u
                LEFT JOIN user_activities ua ON u.id = ua.user_id
                LEFT JOIN user_responses ur ON u.id = ur.user_id
                GROUP BY u.id, u.user_id
                HAVING COUNT(DISTINCT ua.lesson_id) > 0
                ORDER BY completion_percentage ASC
                LIMIT 10
            """
        },
        "sentiment_shift": {
            "description": "⚡ Sentiment Shift / Energy Levels - Energy-related responses over lessons",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_engaged,
                    COUNT(ur.id) as total_responses,
                    COUNT(CASE WHEN ur.response_text ILIKE '%energy%' OR ur.response_text ILIKE '%tired%' OR ur.response_text ILIKE '%energized%' THEN 1 END) as energy_mentions,
                    COUNT(CASE WHEN ur.response_text ILIKE '%tired%' OR ur.response_text ILIKE '%exhausted%' OR ur.response_text ILIKE '%drained%' THEN 1 END) as low_energy,
                    COUNT(CASE WHEN ur.response_text ILIKE '%energized%' OR ur.response_text ILIKE '%motivated%' OR ur.response_text ILIKE '%focused%' THEN 1 END) as high_energy
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "digital_behavior": {
            "description": "📱 Digital Behavior Snapshot - Screen time and device usage patterns",
            "sql": """
                SELECT 
                    CASE 
                        WHEN ur.response_text ILIKE '%5%hour%' OR ur.response_text ILIKE '%6%hour%' OR ur.response_text ILIKE '%7%hour%' THEN '5-7 hours'
                        WHEN ur.response_text ILIKE '%3%hour%' OR ur.response_text ILIKE '%4%hour%' THEN '3-4 hours'
                        WHEN ur.response_text ILIKE '%8%hour%' OR ur.response_text ILIKE '%9%hour%' OR ur.response_text ILIKE '%10%hour%' THEN '8+ hours'
                        WHEN ur.response_text ILIKE '%1%hour%' OR ur.response_text ILIKE '%2%hour%' THEN '1-2 hours'
                        WHEN ur.response_text ILIKE '%screen%' OR ur.response_text ILIKE '%phone%' OR ur.response_text ILIKE '%device%' THEN 'Device Usage'
                        ELSE 'Other'
                    END as screen_time_category,
                    COUNT(*) as user_count,
                    COUNT(DISTINCT ur.user_id) as unique_users
                FROM user_responses ur
                WHERE ur.response_text IS NOT NULL AND ur.response_text != ''
                GROUP BY screen_time_category
                ORDER BY user_count DESC
            """
        },
        "learning_priorities": {
            "description": "🧠 Learning Priorities - What learners rank as most important",
            "sql": """
                SELECT 
                    CASE 
                        WHEN ur.response_text ILIKE '%sleep%' THEN 'Sleep'
                        WHEN ur.response_text ILIKE '%productivity%' OR ur.response_text ILIKE '%focus%' THEN 'Productivity'
                        WHEN ur.response_text ILIKE '%stress%' OR ur.response_text ILIKE '%anxiety%' THEN 'Stress Management'
                        WHEN ur.response_text ILIKE '%social%' OR ur.response_text ILIKE '%connection%' THEN 'Social Connection'
                        WHEN ur.response_text ILIKE '%health%' OR ur.response_text ILIKE '%wellness%' THEN 'Health & Wellness'
                        ELSE 'Other'
                    END as priority_category,
                    COUNT(*) as mention_count,
                    COUNT(DISTINCT ur.user_id) as unique_users
                FROM user_responses ur
                WHERE ur.response_text IS NOT NULL AND ur.response_text != ''
                AND LENGTH(ur.response_text) > 10
                GROUP BY priority_category
                ORDER BY mention_count DESC
            """
        },
        "reflection_themes": {
            "description": "📝 Reflection Themes - Common emotional and behavioral themes",
            "sql": """
                SELECT 
                    CASE 
                        WHEN ur.response_text ILIKE '%lonely%' OR ur.response_text ILIKE '%alone%' THEN 'Loneliness'
                        WHEN ur.response_text ILIKE '%stressed%' OR ur.response_text ILIKE '%overwhelmed%' THEN 'Stress'
                        WHEN ur.response_text ILIKE '%procrastinate%' OR ur.response_text ILIKE '%delay%' THEN 'Procrastination'
                        WHEN ur.response_text ILIKE '%distract%' OR ur.response_text ILIKE '%focus%' THEN 'Distraction'
                        WHEN ur.response_text ILIKE '%improve%' OR ur.response_text ILIKE '%better%' THEN 'Improvement'
                        ELSE 'Other'
                    END as theme_category,
                    COUNT(*) as mention_count,
                    COUNT(DISTINCT ur.user_id) as unique_users
                FROM user_responses ur
                WHERE ur.response_text IS NOT NULL AND ur.response_text != ''
                AND LENGTH(ur.response_text) > 20
                GROUP BY theme_category
                ORDER BY mention_count DESC
            """
        },
        "completion_rates": {
            "description": "Show completion rates for each lesson",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "highest_lowest_completion": {
            "description": "Which lessons have the highest and lowest completion rates",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                HAVING COUNT(DISTINCT ua.user_id) > 0
                ORDER BY completion_rate DESC
            """
        },
        "engagement_over_time": {
            "description": "Show student engagement over time across the course",
            "sql": """
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
        },
        "incomplete_students": {
            "description": "Which students have not finished the course yet",
            "sql": """
                SELECT 
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM lessons) as total_lessons,
                    COUNT(DISTINCT ur.user_id) as users_with_responses,
                    (SELECT COUNT(*) FROM users) - COUNT(DISTINCT ur.user_id) as users_without_responses,
                    CAST(
                        ((SELECT COUNT(*) FROM users) - COUNT(DISTINCT ur.user_id))::float / 
                        (SELECT COUNT(*) FROM users)::float * 100 AS NUMERIC(5,1)
                    ) as incomplete_percentage
                FROM user_responses ur
            """
        },
        "average_completion": {
            "description": "Give me the average completion rate across all lessons",
            "sql": """
                SELECT 
                    CAST(AVG(completion_rate) AS NUMERIC(5,1)) as average_completion_rate,
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
                             NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                        ) as completion_rate
                    FROM lessons l
                    LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                    GROUP BY l.id, l.lesson_number
                    HAVING COUNT(DISTINCT ua.user_id) > 0
                ) as lesson_stats
            """
        },
        "lesson_comparison": {
            "description": "Compare completion rates between specific lessons",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    CAST(
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100 AS NUMERIC(5,1)
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                WHERE l.lesson_number IN (1, 5)
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "completion_speed": {
            "description": "Show how many students completed the course within 30 days of starting",
            "sql": """
                SELECT 
                    u.user_id,
                    u.email,
                    MIN(ua.timestamp) as first_activity,
                    MAX(ua.timestamp) as last_activity,
                    EXTRACT(DAYS FROM MAX(ua.timestamp) - MIN(ua.timestamp)) as days_to_complete,
                    COUNT(DISTINCT ua.lesson_id) as lessons_completed
                FROM users u
                JOIN user_activities ua ON u.id = ua.user_id
                GROUP BY u.id, u.user_id, u.email
                HAVING COUNT(DISTINCT ua.lesson_id) >= (SELECT COUNT(*) FROM lessons) * 0.8
                ORDER BY days_to_complete
            """
        },
        "lesson_completion_rates": {
            "description": "Show engagement rates for each lesson in the course",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_engaged,
                    COUNT(*) as total_activities,
                    CAST(
                        (COUNT(DISTINCT ua.user_id)::float / 
                         (SELECT COUNT(*) FROM users)::float) * 100 AS NUMERIC(5,2)
                    ) as engagement_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                WHERE ua.activity_type = 'http://adlnet.gov/expapi/verbs/answered'
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "highest_lowest_completion": {
            "description": "Which lessons have the highest and lowest engagement rates",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_engaged,
                    COUNT(*) as total_activities,
                    CAST(
                        (COUNT(DISTINCT ua.user_id)::float / 
                         (SELECT COUNT(*) FROM users)::float) * 100 AS NUMERIC(5,2)
                    ) as engagement_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                WHERE ua.activity_type = 'http://adlnet.gov/expapi/verbs/answered'
                GROUP BY l.id, l.lesson_number, l.lesson_name
                HAVING COUNT(DISTINCT ua.user_id) > 0
                ORDER BY engagement_rate DESC
            """
        },
        "student_engagement_over_time": {
            "description": "Show student engagement over time across the course",
            "sql": """
                SELECT 
                    DATE(ua.timestamp) as activity_date,
                    COUNT(DISTINCT ua.user_id) as active_users,
                    COUNT(*) as total_activities
                FROM user_activities ua
                WHERE ua.timestamp >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(ua.timestamp)
                ORDER BY activity_date
            """
        },

        "average_completion_rate": {
            "description": "Give me the average engagement rate across all lessons",
            "sql": """
                SELECT 
                    (AVG(engagement_rate))::numeric(5,2) as average_engagement_rate,
                    COUNT(*) as total_lessons,
                    SUM(users_engaged) as total_engagements,
                    SUM(total_activities) as total_activities
                FROM (
                    SELECT 
                        l.lesson_number,
                        COUNT(DISTINCT ua.user_id) as users_engaged,
                        COUNT(*) as total_activities,
                        CAST(
                            (COUNT(DISTINCT ua.user_id)::float / 
                             (SELECT COUNT(*) FROM users)::float) * 100 AS NUMERIC(5,2)
                        ) as engagement_rate
                    FROM lessons l
                    LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                    WHERE ua.activity_type = 'http://adlnet.gov/expapi/verbs/answered'
                    GROUP BY l.id, l.lesson_number
                    HAVING COUNT(DISTINCT ua.user_id) > 0
                ) as lesson_stats
            """
        },
        "lesson_comparison": {
            "description": "Compare engagement rates between specific lessons",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_engaged,
                    COUNT(*) as total_activities,
                    CAST(
                        (COUNT(DISTINCT ua.user_id)::float / 
                         (SELECT COUNT(*) FROM users)::float) * 100 AS NUMERIC(5,2)
                    ) as engagement_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                WHERE l.lesson_number IN (1, 5) AND ua.activity_type = 'http://adlnet.gov/expapi/verbs/answered'
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "time_to_completion": {
            "description": "Show how many students completed the course within 30 days of starting",
            "sql": """
                SELECT 
                    u.user_id,
                    MIN(ua.timestamp) as first_activity,
                    MAX(ua.timestamp) as last_activity,
                    EXTRACT(DAYS FROM MAX(ua.timestamp) - MIN(ua.timestamp)) as days_to_complete,
                    COUNT(DISTINCT ua.lesson_id) as lessons_engaged,
                    (SELECT COUNT(*) FROM lessons) as total_lessons
                FROM users u
                JOIN user_activities ua ON u.id = ua.user_id
                GROUP BY u.id, u.user_id
                HAVING COUNT(DISTINCT ua.lesson_id) >= (SELECT COUNT(*) FROM lessons) * 0.8
                ORDER BY days_to_complete
            """
        },
        "habit_changes": {
            "description": "Get evidence of habit changes across lessons",
            "sql": """
                SELECT u.user_id, l.lesson_number, l.lesson_name, ur.response_text, ur.timestamp
                FROM users u 
                JOIN user_responses ur ON u.id = ur.user_id 
                JOIN questions q ON ur.question_id = q.id 
                JOIN lessons l ON q.lesson_id = l.id 
                WHERE ur.response_text IS NOT NULL 
                AND ur.response_text != '' 
                AND ur.response_text NOT LIKE '%—%' 
                AND ur.response_text NOT LIKE '%👍%'
                AND LENGTH(ur.response_text) > 20
                ORDER BY u.user_id, l.lesson_number, ur.timestamp
                LIMIT 50
            """
        },
        "top_users": {
            "description": "Get most engaged users",
            "sql": """
                SELECT u.user_id, COUNT(ua.id) as activity_count, 
                       MIN(ua.timestamp) as first_activity, MAX(ua.timestamp) as last_activity
                FROM users u 
                LEFT JOIN user_activities ua ON u.id = ua.user_id 
                GROUP BY u.id, u.user_id 
                ORDER BY activity_count DESC 
                LIMIT 10
            """
        },
        "lesson_completion": {
            "description": "Get lesson completion rates",
            "sql": """
                SELECT l.lesson_number, l.lesson_name, COUNT(DISTINCT ua.user_id) as users_completed
                FROM lessons l 
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id 
                GROUP BY l.id, l.lesson_number, l.lesson_name 
                ORDER BY l.lesson_number
            """
        },
        "recent_activity": {
            "description": "Get recent user activity",
            "sql": """
                SELECT u.user_id, l.lesson_name, ua.activity_type, ua.timestamp
                FROM users u 
                JOIN user_activities ua ON u.id = ua.user_id 
                JOIN lessons l ON ua.lesson_id = l.id 
                ORDER BY ua.timestamp DESC 
                LIMIT 20
            """
        },
        "screen_time_responses": {
            "description": "Get responses about screen time habits",
            "sql": """
                SELECT u.user_id, l.lesson_number, ur.response_text, ur.timestamp
                FROM users u 
                JOIN user_responses ur ON u.id = ur.user_id 
                JOIN questions q ON ur.question_id = q.id 
                JOIN lessons l ON q.lesson_id = l.id 
                WHERE ur.response_text ILIKE '%screen%' 
                OR ur.response_text ILIKE '%phone%' 
                OR ur.response_text ILIKE '%device%'
                ORDER BY ur.timestamp DESC 
                LIMIT 30
            """
        },
        "lesson_details": {
            "description": "Get lesson details with questions and sample responses",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    q.question_number,
                    q.question_text,
                    ur.response_text,
                    u.user_id,
                    ur.timestamp
                FROM lessons l
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                LEFT JOIN users u ON ur.user_id = u.id
                WHERE l.lesson_number = 1
                ORDER BY q.question_number, ur.timestamp DESC
                LIMIT 20
            """
        },
        "engagement_health": {
            "description": "Overall engagement health - completion rates and drop-off analysis",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_reached,
                    COUNT(ur.id) as total_responses
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "lesson_engagement": {
            "description": "Which lessons are most/least engaging - response counts and activity",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_reached,
                    COUNT(ur.id) as total_responses
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY COUNT(ur.id) DESC
            """
        },
        "behavior_priorities": {
            "description": "Which behaviors (sleep, stress, focus) resonate most with cohort",
            "sql": """
                SELECT 
                    CASE 
                        WHEN ur.response_text ILIKE '%sleep%' THEN 'Sleep'
                        WHEN ur.response_text ILIKE '%stress%' THEN 'Stress'
                        WHEN ur.response_text ILIKE '%focus%' OR ur.response_text ILIKE '%productivity%' THEN 'Focus/Productivity'
                        WHEN ur.response_text ILIKE '%screen%' OR ur.response_text ILIKE '%device%' THEN 'Screen Time'
                        ELSE 'Other'
                    END as behavior_category,
                    COUNT(*) as mention_count,
                    COUNT(DISTINCT ur.user_id) as unique_users
                FROM user_responses ur
                WHERE ur.response_text IS NOT NULL 
                AND ur.response_text != ''
                AND LENGTH(ur.response_text) > 10
                GROUP BY behavior_category
                ORDER BY mention_count DESC
            """
        },
        "student_impact": {
            "description": "Did students actually change behavior - pre/post insights",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ur.user_id) as students_engaged,
                    COUNT(ur.id) as total_responses,
                    COUNT(CASE WHEN ur.response_text ILIKE '%improve%' OR ur.response_text ILIKE '%better%' THEN 1 END) as positive_changes,
                    CAST((COUNT(CASE WHEN ur.response_text ILIKE '%improve%' OR ur.response_text ILIKE '%better%' THEN 1 END) * 100.0 / COUNT(ur.id)) AS NUMERIC(5,1)) as improvement_rate
                FROM lessons l
                LEFT JOIN user_responses ur ON l.id = ur.lesson_id
                WHERE ur.response_text IS NOT NULL
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "unique_insights": {
            "description": "What unique student insights can we provide - vulnerability and reflection themes",
            "sql": """
                SELECT 
                    ur.response_text,
                    u.user_id,
                    l.lesson_name,
                    ur.timestamp
                FROM user_responses ur
                JOIN users u ON ur.user_id = u.id
                JOIN questions q ON ur.question_id = q.id
                JOIN lessons l ON q.lesson_id = l.id
                WHERE ur.response_text IS NOT NULL 
                AND ur.response_text != ''
                AND LENGTH(ur.response_text) > 50
                AND (ur.response_text ILIKE '%struggle%' 
                     OR ur.response_text ILIKE '%difficult%'
                     OR ur.response_text ILIKE '%challenge%'
                     OR ur.response_text ILIKE '%hard%'
                     OR ur.response_text ILIKE '%need%'
                     OR ur.response_text ILIKE '%want%')
                ORDER BY ur.timestamp DESC
                LIMIT 15
            """
        },
        "lesson_details": {
            "description": "Get lesson details with questions and sample responses",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    q.question_number,
                    q.question_text,
                    COUNT(DISTINCT ur.user_id) as response_count,
                    ur.response_text as sample_response,
                    ur.timestamp
                FROM lessons l
                LEFT JOIN questions q ON l.id = q.lesson_id
                LEFT JOIN user_responses ur ON q.id = ur.question_id
                WHERE l.lesson_number = 1
                AND ur.response_text IS NOT NULL
                AND ur.response_text != ''
                ORDER BY l.lesson_number, q.question_number, ur.timestamp DESC
                LIMIT 20
            """
        }
    }

def get_all_database_content():
    """Get relevant database content for LLM context (limited to fit token limits)"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get lessons (limited)
            cur.execute("""
                SELECT id, lesson_number, lesson_name 
                FROM lessons 
                ORDER BY lesson_number
                LIMIT 10
            """)
            lessons = [dict(row) for row in cur.fetchall()]
            
            # Get questions (limited)
            cur.execute("""
                SELECT q.id, q.question_number, q.question_text, q.lesson_id,
                       l.lesson_number, l.lesson_name
                FROM questions q
                JOIN lessons l ON q.lesson_id = l.id
                ORDER BY l.lesson_number, q.question_number
                LIMIT 20
            """)
            questions = [dict(row) for row in cur.fetchall()]
            
            # Get key user responses (limited and focused on important topics)
            cur.execute("""
                SELECT ur.id, ur.response_text, ur.user_id, ur.timestamp,
                       q.question_text, q.question_number,
                       l.lesson_number, l.lesson_name
                FROM user_responses ur
                JOIN questions q ON ur.question_id = q.id
                JOIN lessons l ON q.lesson_id = l.id
                WHERE ur.response_text IS NOT NULL 
                AND ur.response_text != ''
                AND (
                    ur.response_text ILIKE '%sleep%' OR
                    ur.response_text ILIKE '%energy%' OR
                    ur.response_text ILIKE '%screen%' OR
                    ur.response_text ILIKE '%phone%' OR
                    ur.response_text ILIKE '%priority%' OR
                    ur.response_text ILIKE '%stress%' OR
                    ur.response_text ILIKE '%tired%' OR
                    ur.response_text ILIKE '%focus%' OR
                    ur.response_text ILIKE '%habit%' OR
                    ur.response_text ILIKE '%improve%'
                )
                ORDER BY ur.timestamp DESC
                LIMIT 30
            """)
            responses = [dict(row) for row in cur.fetchall()]
            
            # Get user activities (limited)
            cur.execute("""
                SELECT ua.id, ua.user_id, ua.activity_type, ua.timestamp,
                       l.lesson_number, l.lesson_name
                FROM user_activities ua
                JOIN lessons l ON ua.lesson_id = l.id
                ORDER BY ua.timestamp DESC
                LIMIT 20
            """)
            activities = [dict(row) for row in cur.fetchall()]
            
            # Get user info (limited)
            cur.execute("""
                SELECT id, user_id, created_at
                FROM users
                ORDER BY created_at
                LIMIT 10
            """)
            users = [dict(row) for row in cur.fetchall()]
            
            # Convert datetime objects to strings for JSON serialization
            def convert_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif hasattr(obj, 'quantize'):  # Decimal objects
                    return str(obj)
                return obj
            
            def clean_dict(d):
                return {k: convert_datetime(v) for k, v in d.items()}
            
            def clean_list_of_dicts(lst):
                return [clean_dict(d) for d in lst]
            
            return {
                "lessons": clean_list_of_dicts(lessons),
                "questions": clean_list_of_dicts(questions),
                "responses": clean_list_of_dicts(responses),
                "activities": clean_list_of_dicts(activities),
                "users": clean_list_of_dicts(users)
            }
    except Exception as e:
        print(f"Error fetching database content: {e}")
        return {"error": str(e)}
    finally:
        conn.close()

def execute_query(sql_query):
    """Execute a SQL query and return results"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            results = cur.fetchall()
            
            # Convert datetime objects and Decimal to strings for JSON serialization
            def convert_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                elif hasattr(obj, 'quantize'):  # Decimal objects
                    return str(obj)
                return obj
            
            def clean_dict(d):
                return {k: convert_datetime(v) for k, v in d.items()}
            
            return [clean_dict(dict(row)) for row in results]
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
    finally:
        conn.close()

def get_llm_intent_and_sql(user_message: str, schema: Dict, sample_data: Dict) -> Dict[str, Any]:
    """Use LLM to determine intent and generate SQL"""
    client = get_openai_client()
    
    # Get all database content for context
    all_database_content = get_all_database_content()
    
    # Create context with schema, all database content, and preloaded queries
    context = f"""
Database Schema:
{json.dumps(schema, indent=2)}

Complete Database Content:
{json.dumps(all_database_content, indent=2)}

Preloaded Queries Available:
{json.dumps(sample_data, indent=2)}

User Question: {user_message}

CRITICAL INSTRUCTIONS:
1. You MUST return a JSON object with exactly this format: {{"intent": "description", "sql": "query_name", "explanation": "what this does"}}
2. For "sql" field, use ONLY the exact query name from the preloaded queries (engagement_dropoff, problematic_users, sentiment_shift, digital_behavior, learning_priorities, reflection_themes)
3. DO NOT generate custom SQL - only use the preloaded query names
4. DO NOT make up numbers or data - you must execute the actual query
5. For specific topic questions (like "sleep", "energy", "screen time"), analyze the Complete Database Content to find relevant responses and choose the most appropriate preloaded query
6. For engagement questions, use "engagement_dropoff"
7. For user behavior questions, use "digital_behavior"
8. For priority questions, use "learning_priorities"

Available Preloaded Queries:
- engagement_dropoff: 📉 Engagement Drop-Off - Lesson completion funnel
- problematic_users: 🚨 Problematic Users - Learners with low completion or engagement  
- sentiment_shift: ⚡ Sentiment Shift / Energy Levels - Energy-related responses over lessons
- digital_behavior: 📱 Digital Behavior Snapshot - Screen time and device usage patterns
- learning_priorities: 🧠 Learning Priorities - What learners rank as most important
- reflection_themes: 📝 Reflection Themes - Common emotional and behavioral themes

EXAMPLE RESPONSES:
- "show engagement dropoff" → {{"intent": "engagement_analysis", "sql": "engagement_dropoff", "explanation": "Get lesson completion funnel"}}
- "problematic users" → {{"intent": "user_analysis", "sql": "problematic_users", "explanation": "Get users with low completion rates"}}
- "energy levels" → {{"intent": "sentiment_analysis", "sql": "sentiment_shift", "explanation": "Get energy-related responses over lessons"}}
- "screen time" → {{"intent": "behavior_analysis", "sql": "digital_behavior", "explanation": "Get screen time usage patterns"}}
- "learning priorities" → {{"intent": "priority_analysis", "sql": "learning_priorities", "explanation": "Get what learners prioritize most"}}
- "reflection themes" → {{"intent": "theme_analysis", "sql": "reflection_themes", "explanation": "Get common emotional themes"}}
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a SQL expert. You MUST return valid JSON with preloaded query names. NEVER make up data or numbers. ALWAYS use the exact query names provided."},
            {"role": "user", "content": context}
        ],
        max_tokens=500,
        temperature=0.0
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        # Validate that the result has the required fields and uses a valid query name
        if not isinstance(result, dict) or 'sql' not in result:
            raise ValueError("Invalid response format")
        
        # Ensure sql field is a valid preloaded query name
        valid_queries = ['engagement_dropoff', 'problematic_users', 'sentiment_shift', 'digital_behavior', 'learning_priorities', 'reflection_themes']
        if result.get('sql') not in valid_queries:
            # Force use of engagement_dropoff query if invalid
            result['sql'] = 'engagement_dropoff'
            result['intent'] = 'fallback_query'
            result['explanation'] = 'Using engagement dropoff query as fallback'
        
        return result
    except (json.JSONDecodeError, ValueError, KeyError):
        # Fallback if JSON parsing fails or invalid response
        return {
            "intent": "fallback_query",
            "sql": "stats",
            "explanation": "Using stats query as fallback for general queries"
        }

def generate_visualization(results: List[Dict], intent: str) -> Optional[str]:
    """Generate Plotly visualization based on query results and intent"""
    if not results or len(results) == 0:
        return None
    
    try:
        # Convert datetime objects for JSON serialization
        def convert_datetime(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return obj
        
        def clean_dict(d):
            return {k: convert_datetime(v) for k, v in d.items()}
        
        cleaned_results = [clean_dict(result) for result in results]
        
        # Generate different visualizations based on intent and data structure
        if 'engagement' in intent.lower() or 'dropoff' in intent.lower():
            if cleaned_results and 'completion_rate' in cleaned_results[0]:
                # Completion rates and engagement dropoff chart
                fig = go.Figure()
                
                # Add completion rate bars
                fig.add_trace(go.Bar(
                    x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                    y=[float(r.get('completion_rate', 0)) for r in cleaned_results],
                    name='Completion Rate (%)',
                    marker_color='#6366f1',
                    text=[f"{r.get('completion_rate', 0)}%" for r in cleaned_results],
                    textposition='auto',
                    yaxis='y'
                ))
                
                # Add users engaged line (engagement dropoff)
                fig.add_trace(go.Scatter(
                    x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                    y=[r.get('users_engaged', 0) for r in cleaned_results],
                    name='Users Engaged',
                    mode='lines+markers',
                    line=dict(color='#ef4444', width=3),
                    marker=dict(size=8),
                    yaxis='y2'
                ))
                
                fig.update_layout(
                    title='Engagement Dropoff & Completion Rates',
                    xaxis_title='Lesson',
                    yaxis=dict(
                        title='Completion Rate (%)',
                        range=[0, 100],
                        side='left'
                    ),
                    yaxis2=dict(
                        title='Users Engaged',
                        side='right',
                        overlaying='y'
                    ),
                    template='plotly_white',
                    height=400,
                    legend=dict(x=0.02, y=0.98)
                )
                return fig.to_json()
            elif cleaned_results and 'average_completion_rate' in cleaned_results[0]:
                # Single metric display
                avg_rate = cleaned_results[0].get('average_completion_rate', 0)
                fig = go.Figure(data=[
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=float(avg_rate),
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Average Completion Rate (%)"},
                        gauge={'axis': {'range': [None, 100]},
                               'bar': {'color': "#6366f1"},
                               'steps': [{'range': [0, 50], 'color': "lightgray"},
                                        {'range': [50, 80], 'color': "yellow"},
                                        {'range': [80, 100], 'color': "green"}]}
                    )
                ])
                fig.update_layout(template='plotly_white', height=400)
                return fig.to_json()
        
        elif 'engagement' in intent.lower() or 'lesson' in intent.lower():
            if cleaned_results and 'lesson_number' in cleaned_results[0]:
                # Lesson engagement chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                        y=[r.get('total_responses', r.get('users_reached', r.get('users_engaged', 0))) for r in cleaned_results],
                        name='User Engagement',
                        marker_color='#48bb78',
                        text=[str(r.get('total_responses', r.get('users_reached', r.get('users_engaged', 0)))) for r in cleaned_results],
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title='Lesson Engagement',
                    xaxis_title='Lesson',
                    yaxis_title='Users Engaged',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        elif 'behavior' in intent.lower() or 'priority' in intent.lower() or 'digital' in intent.lower():
            if cleaned_results and ('priority_category' in cleaned_results[0] or 'screen_time_category' in cleaned_results[0]):
                # Learning priorities or digital behavior pie chart
                category_key = 'priority_category' if 'priority_category' in cleaned_results[0] else 'screen_time_category'
                value_key = 'mention_count' if 'mention_count' in cleaned_results[0] else 'user_count'
                
                fig = go.Figure(data=[
                    go.Pie(
                        labels=[r.get(category_key, 'Other') for r in cleaned_results],
                        values=[r.get(value_key, 0) for r in cleaned_results],
                        hole=0.3,
                        textinfo='label+percent',
                        textposition='inside'
                    )
                ])
                fig.update_layout(
                    title='Learning Priorities' if 'priority_category' in cleaned_results[0] else 'Screen Time Distribution',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        elif 'sentiment' in intent.lower() or 'energy' in intent.lower():
            if cleaned_results and 'lesson_number' in cleaned_results[0]:
                # Energy levels over lessons line chart
                fig = go.Figure()
                
                # Add low energy line
                fig.add_trace(go.Scatter(
                    x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                    y=[r.get('low_energy', 0) for r in cleaned_results],
                    mode='lines+markers',
                    name='Low Energy',
                    line=dict(color='red', width=3),
                    marker=dict(size=8)
                ))
                
                # Add high energy line
                fig.add_trace(go.Scatter(
                    x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                    y=[r.get('high_energy', 0) for r in cleaned_results],
                    mode='lines+markers',
                    name='High Energy',
                    line=dict(color='green', width=3),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title='Energy Levels Over Lessons',
                    xaxis_title='Lesson',
                    yaxis_title='Number of Responses',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        elif 'theme' in intent.lower() or 'reflection' in intent.lower():
            if cleaned_results and 'theme_category' in cleaned_results[0]:
                # Reflection themes bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=[r.get('theme_category', 'Other') for r in cleaned_results],
                        y=[r.get('mention_count', 0) for r in cleaned_results],
                        name='Theme Mentions',
                        marker_color='#8b5cf6',
                        text=[str(r.get('mention_count', 0)) for r in cleaned_results],
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title='Reflection Themes',
                    xaxis_title='Theme',
                    yaxis_title='Number of Mentions',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        elif 'problematic' in intent.lower() or 'user' in intent.lower():
            if cleaned_results and 'completion_percentage' in cleaned_results[0]:
                # Problematic users scatter plot
                fig = go.Figure(data=[
                    go.Scatter(
                        x=[r.get('completion_percentage', 0) for r in cleaned_results],
                        y=[r.get('total_responses', 0) for r in cleaned_results],
                        mode='markers',
                        name='Users',
                        marker=dict(
                            size=10,
                            color=[r.get('completion_percentage', 0) for r in cleaned_results],
                            colorscale='RdYlGn',
                            showscale=True,
                            colorbar=dict(title="Completion %")
                        ),
                        text=[r.get('user_id', 'Unknown') for r in cleaned_results],
                        hovertemplate='User: %{text}<br>Completion: %{x}%<br>Responses: %{y}<extra></extra>'
                    )
                ])
                fig.update_layout(
                    title='User Completion vs Engagement',
                    xaxis_title='Completion Percentage',
                    yaxis_title='Total Responses',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        elif 'user' in intent.lower() or 'stats' in intent.lower() or 'incomplete' in intent.lower():
            # Simple bar chart for user stats and incomplete students
            keys = list(cleaned_results[0].keys())
            numeric_keys = [k for k in keys if isinstance(cleaned_results[0][k], (int, float))]
            if numeric_keys:
                fig = go.Figure(data=[
                    go.Bar(
                        x=[k.replace('_', ' ').title() for k in numeric_keys],
                        y=[cleaned_results[0][k] for k in numeric_keys],
                        name='Count',
                        marker_color='#ed8936',
                        text=[str(cleaned_results[0][k]) for k in numeric_keys],
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title='Student Completion Status',
                    xaxis_title='Metric',
                    yaxis_title='Count',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        # Add time-based visualization for engagement over time
        elif 'time' in intent.lower() or 'trend' in intent.lower():
            if cleaned_results and 'activity_date' in cleaned_results[0]:
                # Time series chart for engagement over time
                fig = go.Figure(data=[
                    go.Scatter(
                        x=[r.get('activity_date') for r in cleaned_results],
                        y=[r.get('active_users', r.get('users_engaged', 0)) for r in cleaned_results],
                        mode='lines+markers',
                        name='Active Users',
                        line=dict(color='#667eea', width=3),
                        marker=dict(size=8)
                    )
                ])
                fig.update_layout(
                    title='Student Engagement Over Time',
                    xaxis_title='Date',
                    yaxis_title='Active Users',
                    template='plotly_white',
                    height=400
                )
                return fig.to_json()
        
        return None
    except Exception as e:
        print(f"Visualization generation failed: {e}")
        return None

def format_query_results(results: List[Dict], intent: str) -> str:
    """Format query results into readable text"""
    if not results:
        return "No data found for this query."
    
    # Convert datetime objects to strings for JSON serialization
    def convert_datetime(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj
    
    def clean_dict(d):
        return {k: convert_datetime(v) for k, v in d.items()}
    
    cleaned_results = [clean_dict(result) for result in results]
    
    if len(cleaned_results) == 1:
        # Single result
        result = cleaned_results[0]
        if 'count' in result or 'total' in result:
            return f"Found {result.get('count', result.get('total', 0))} records."
        else:
            return f"Result: {json.dumps(result, indent=2)}"
    
    # Multiple results - summarize
    if len(cleaned_results) <= 5:
        return f"Found {len(cleaned_results)} results:\n" + "\n".join([f"- {json.dumps(r)}" for r in cleaned_results])
    else:
        return f"Found {len(cleaned_results)} results. Showing first 5:\n" + "\n".join([f"- {json.dumps(r)}" for r in cleaned_results[:5]])

@router.post("/chat", 
    response_model=ChatResponse,
    summary="Chat with AI Assistant",
    description="Send a message to the AI assistant and get a response with optional visualization",
    responses={
        200: {
            "description": "Successfully processed chat request",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Based on the data, you have 150 total users with 85% completion rate across all lessons. The most engaging lesson is 'Core Concepts' with 92% completion.",
                        "visualization": "<div id='chart'><script>Plotly.newPlot('chart', data, layout);</script></div>"
                    }
                }
            }
        },
        400: {
            "description": "Invalid request format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid request format"
                    }
                }
            }
        }
    }
)
async def chat(request: ChatRequest):
    """Handle chat requests with LLM-driven intent detection and SQL generation"""
    
    try:
        # Initialize OpenAI client
        client = get_openai_client()
        
        # Get preloaded queries and schema
        preloaded_queries = get_preloaded_queries()
        schema = get_database_schema()
        
        # Use LLM to determine intent and generate SQL
        llm_result = get_llm_intent_and_sql(request.message, schema, preloaded_queries)
        
        # Execute the generated SQL or use preloaded queries
        try:
            print(f"DEBUG: LLM returned query name: {llm_result['sql']}")
            print(f"DEBUG: Available queries: {list(preloaded_queries.keys())}")
            
            if llm_result['sql'] in preloaded_queries:
                # Use preloaded query
                query_sql = preloaded_queries[llm_result['sql']]['sql']
                print(f"DEBUG: Executing preloaded query: {llm_result['sql']}")
                query_results = execute_query(query_sql)
                print(f"DEBUG: Query returned {len(query_results)} results")
                data_summary = format_query_results(query_results, llm_result['intent'])
            else:
                print(f"DEBUG: Query name '{llm_result['sql']}' not found in preloaded queries")
                # Fallback to engagement_dropoff query
                query_sql = preloaded_queries['engagement_dropoff']['sql']
                query_results = execute_query(query_sql)
                data_summary = format_query_results(query_results, 'fallback')
        except Exception as e:
            print(f"DEBUG: Query execution failed: {str(e)}")
            data_summary = f"Query execution failed: {str(e)}"
            query_results = []
        
        # Generate visualization if we have results
        visualization = None
        if query_results:
            visualization = generate_visualization(query_results, llm_result['intent'])
        
        # Prepare conversation history with dynamic schema context
        # Get all database content for context
        all_database_content = get_all_database_content()
        
        # Create a simplified schema summary for the LLM
        schema_summary = {}
        for table_name, columns in schema.items():
            schema_summary[table_name] = [col['column'] for col in columns[:5]]  # Limit to first 5 columns
        
        messages = [
            {
                "role": "system",
                "content": f"""You are Seven, an AI analytics assistant for course completion data. Follow these DEMO-READY formatting rules:

Database Schema:
{json.dumps(schema_summary, indent=2)}

Complete Database Content:
{json.dumps(all_database_content, indent=2)}

Available Queries: engagement_dropoff, problematic_users, sentiment_shift, digital_behavior, learning_priorities, reflection_themes

FORMATTING RULES:
1. ALWAYS put text summary ABOVE any visualization
2. Keep text concise but informative (2-4 sentences)
3. Use specific numbers and percentages from the data
4. For engagement data, focus on user counts (users_engaged) rather than percentages
4. For engagement dropoff: "Lesson X has Y% completion rate with Z users engaged, showing dropoff from A users in Lesson X-1 to B users in Lesson X"
5. For problematic users: "X users have completion rates below 50%, with Y users stuck at Lesson Z"
6. For sentiment shift: "Energy levels shift from X% low energy at start to Y% energized by Lesson Z"
7. For digital behavior: "Most learners report X-Y hours daily screen time, with Z% in the high usage category"
8. For learning priorities: "X% ranked Sleep as top priority, followed by Y% for Productivity"
9. For reflection themes: "Loneliness is the most common theme (X mentions), especially tied to high screen time"
10. Never use emojis - keep professional tone
11. If no data found, say "No data available for this analysis"

EXAMPLE RESPONSES:
- "Lesson 3 shows the steepest drop-off with 0% completion rate and 7 users engaged, down from 8 users in Lesson 2."
- "8 users have completion rates below 50%, with 3 users stuck at Lesson 2."
- "Energy levels improve from 70% low energy at start to 55% energized by Lesson 6."
- "Most learners report 5-7 hours daily screen time, with 60% in the high usage category."
- "45% ranked Sleep as their top priority, followed by Productivity at 30%."
- "Loneliness is the most common emotional theme (25 mentions), especially tied to high screen time."""
            }
        ]
        
        # Add conversation history (keep full context)
        for msg in request.history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message with simplified context
        current_message = f"""
User: {request.message}

Query Results: {data_summary}

IMPORTANT: For engagement dropoff analysis, focus on the 'users_engaged' field (actual user counts) rather than percentage rates. Use the format: "Lesson X has Y users engaged with Z% completion rate."

Please provide a concise response based on the query results."""
        
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        # Generate response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        return ChatResponse(
            response=response.choices[0].message.content,
            visualization=visualization
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/chat/health")
async def chat_health():
    """Health check for chat service"""
    return {"status": "healthy", "service": "chat"}

# Composable Sub-App Contract Endpoints
@router.post("/chat/query", 
    response_model=AIChatActionResponse,
    summary="AIChat.ask_question action",
    description="Ask a question and get AI-powered response with data analysis"
)
async def ai_chat_ask_question(request: AIChatActionRequest):
    """AIChat.ask_question action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "ask_question":
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'ask_question'"
            )
        
        if not request.query:
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Query is required for ask_question action"
            )
        
        # Get preloaded queries and schema
        preloaded_queries = get_preloaded_queries()
        schema = get_database_schema()
        
        # Use LLM to determine intent and generate SQL
        llm_result = get_llm_intent_and_sql(request.query, schema, preloaded_queries)
        
        # Execute the query
        try:
            if llm_result['sql'] in preloaded_queries:
                query_sql = preloaded_queries[llm_result['sql']]['sql']
                query_results = execute_query(query_sql)
                data_summary = format_query_results(query_results, llm_result['intent'])
            else:
                # Fallback to engagement_dropoff query
                query_sql = preloaded_queries['engagement_dropoff']['sql']
                query_results = execute_query(query_sql)
                data_summary = format_query_results(query_results, 'fallback')
        except Exception as e:
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error=f"Query execution failed: {str(e)}"
            )
        
        # Generate visualization
        visualization = None
        if query_results:
            visualization = generate_visualization(query_results, llm_result['intent'])
        
        # Generate AI response
        client = get_openai_client()
        schema_summary = {}
        for table_name, columns in schema.items():
            schema_summary[table_name] = [col['column'] for col in columns[:5]]
        
        messages = [
            {
                "role": "system",
                "content": f"""You are Seven, an AI analytics assistant. Provide concise, data-driven responses.

Database Schema: {json.dumps(schema_summary, indent=2)}

Query Results: {data_summary}

Respond in 2-3 sentences with specific numbers and insights."""
            },
            {
                "role": "user",
                "content": request.query
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        
        # Calculate confidence based on data availability
        confidence = 0.8 if query_results else 0.3
        
        return AIChatActionResponse(
            success=True,
            action=request.action,
            text=response.choices[0].message.content,
            chart=json.loads(visualization) if visualization else None,
            table={"data": query_results[:10], "columns": list(query_results[0].keys()) if query_results else []},
            confidence=confidence
        )
        
    except Exception as e:
        return AIChatActionResponse(
            success=False,
            action=request.action,
            error=f"Action failed: {str(e)}"
        )

@router.post("/chat/analyze",
    response_model=AIChatActionResponse,
    summary="AIChat.analyze_data action",
    description="Analyze provided data and generate insights"
)
async def ai_chat_analyze_data(request: AIChatActionRequest):
    """AIChat.analyze_data action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "analyze_data":
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'analyze_data'"
            )
        
        if not request.data:
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Data is required for analyze_data action"
            )
        
        # Generate analysis using OpenAI
        client = get_openai_client()
        
        analysis_prompt = f"""
Analyze the following data and provide insights:

Data: {json.dumps(request.data, indent=2)}
Analysis Type: {request.analysis_type or 'general'}

Provide:
1. Key insights (3-5 bullet points)
2. Summary (2-3 sentences)
3. Recommendations (2-3 actionable items)

Format as JSON:
{{
    "insights": ["insight1", "insight2", "insight3"],
    "summary": "brief summary",
    "recommendations": ["rec1", "rec2", "rec3"]
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=500,
            temperature=0.7
        )
        
        try:
            analysis_result = json.loads(response.choices[0].message.content)
            return AIChatActionResponse(
                success=True,
                action=request.action,
                insights=analysis_result.get("insights", []),
                summary=analysis_result.get("summary", ""),
                recommendations=analysis_result.get("recommendations", [])
            )
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return AIChatActionResponse(
                success=True,
                action=request.action,
                insights=["Data analysis completed"],
                summary=response.choices[0].message.content[:200],
                recommendations=["Review the data for patterns", "Consider additional metrics"]
            )
        
    except Exception as e:
        return AIChatActionResponse(
            success=False,
            action=request.action,
            error=f"Analysis failed: {str(e)}"
        )

@router.post("/chat/chart",
    response_model=AIChatActionResponse,
    summary="AIChat.generate_chart action",
    description="Generate chart visualization from provided data"
)
async def ai_chat_generate_chart(request: AIChatActionRequest):
    """AIChat.generate_chart action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "generate_chart":
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'generate_chart'"
            )
        
        if not request.data:
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error="Data is required for generate_chart action"
            )
        
        # Generate chart based on data and chart type
        chart_type = request.chart_type or "bar"
        
        try:
            if chart_type == "bar":
                # Create bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(request.data.keys()),
                        y=list(request.data.values()),
                        name='Data'
                    )
                ])
                fig.update_layout(
                    title='Data Visualization',
                    xaxis_title='Categories',
                    yaxis_title='Values',
                    template='plotly_white'
                )
            elif chart_type == "pie":
                # Create pie chart
                fig = go.Figure(data=[
                    go.Pie(
                        labels=list(request.data.keys()),
                        values=list(request.data.values())
                    )
                ])
                fig.update_layout(title='Data Distribution')
            elif chart_type == "line":
                # Create line chart
                fig = go.Figure(data=[
                    go.Scatter(
                        x=list(request.data.keys()),
                        y=list(request.data.values()),
                        mode='lines+markers'
                    )
                ])
                fig.update_layout(
                    title='Data Trend',
                    xaxis_title='Time/Sequence',
                    yaxis_title='Values'
                )
            else:
                # Default to bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=list(request.data.keys()),
                        y=list(request.data.values()),
                        name='Data'
                    )
                ])
                fig.update_layout(title='Data Visualization')
            
            chart_json = json.loads(fig.to_json())
            
            return AIChatActionResponse(
                success=True,
                action=request.action,
                chart=chart_json,
                config={"displayModeBar": True, "responsive": True}
            )
            
        except Exception as e:
            return AIChatActionResponse(
                success=False,
                action=request.action,
                error=f"Chart generation failed: {str(e)}"
            )
        
    except Exception as e:
        return AIChatActionResponse(
            success=False,
            action=request.action,
            error=f"Chart action failed: {str(e)}"
        )

@router.get("/chat/contract", summary="Get AIChat app contract")
async def get_ai_chat_contract():
    """Get the AIChat app contract for orchestrator integration"""
    return {
        "name": "AIChat",
        "description": "Natural language analytics assistant",
        "actions": [
            {
                "name": "ask_question",
                "input": {"query": "string"},
                "output": {
                    "text": "string",
                    "chart": "object",
                    "table": "object", 
                    "confidence": "float"
                }
            },
            {
                "name": "analyze_data",
                "input": {"data": "object", "analysis_type": "string"},
                "output": {
                    "insights": "list",
                    "summary": "string",
                    "recommendations": "list"
                }
            },
            {
                "name": "generate_chart",
                "input": {"data": "object", "chart_type": "string"},
                "output": {
                    "chart": "object",
                    "config": "object"
                }
            }
        ],
        "endpoints": {
            "ask_question": "POST /api/chat/query",
            "analyze_data": "POST /api/chat/analyze", 
            "generate_chart": "POST /api/chat/chart"
        }
    }
