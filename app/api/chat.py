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

router = APIRouter()

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
        "stats": {
            "description": "Get current database statistics",
            "sql": """
                SELECT 
                    (SELECT COUNT(*) FROM statements_new) as total_statements,
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM lessons) as total_lessons,
                    (SELECT COUNT(*) FROM user_responses) as total_responses,
                    (SELECT COUNT(*) FROM user_activities) as total_activities
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
                    ((
                        (COUNT(DISTINCT ua.user_id)::float / 
                         (SELECT COUNT(*) FROM users)::float) * 100, 2
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
                    ((
                        (COUNT(DISTINCT ua.user_id)::float / 
                         (SELECT COUNT(*) FROM users)::float) * 100, 2
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
        "incomplete_students": {
            "description": "Which students have not finished the course yet",
            "sql": """
                SELECT 
                    u.user_id,
                    u.email,
                    COUNT(DISTINCT ua.lesson_id) as lessons_started,
                    (SELECT COUNT(*) FROM lessons) as total_lessons,
                    (SELECT COUNT(*) FROM lessons) - COUNT(DISTINCT ua.lesson_id) as lessons_remaining
                FROM users u
                LEFT JOIN user_activities ua ON u.id = ua.user_id
                GROUP BY u.id, u.user_id, u.email
                HAVING COUNT(DISTINCT ua.lesson_id) < (SELECT COUNT(*) FROM lessons)
                ORDER BY lessons_remaining DESC
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
                        ((
                            (COUNT(DISTINCT ua.user_id)::float / 
                             (SELECT COUNT(*) FROM users)::float) * 100, 2
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
            "description": "Compare completion rates between specific lessons",
            "sql": """
                SELECT 
                    l.lesson_number,
                    l.lesson_name,
                    COUNT(DISTINCT ua.user_id) as users_started,
                    COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                    ((
                        (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                         NULLIF(COUNT(DISTINCT ua.user_id), 0)::float) * 100, 2
                    ) as completion_rate
                FROM lessons l
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                WHERE l.lesson_number IN (1, 5)
                GROUP BY l.id, l.lesson_number, l.lesson_name
                ORDER BY l.lesson_number
            """
        },
        "time_to_completion": {
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
                    ((COUNT(CASE WHEN ur.response_text ILIKE '%improve%' OR ur.response_text ILIKE '%better%' THEN 1 END) * 100.0 / COUNT(ur.id), 1) as improvement_rate
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

def execute_query(sql_query):
    """Execute a SQL query and return results"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            results = cur.fetchall()
            
            # Convert datetime objects to strings for JSON serialization
            def convert_datetime(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
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
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create context with schema and preloaded queries
    context = f"""
Database Schema:
{json.dumps(schema, indent=2)}

Preloaded Queries Available:
{json.dumps(sample_data, indent=2)}

User Question: {user_message}

CRITICAL INSTRUCTIONS:
1. You MUST return a JSON object with exactly this format: {{"intent": "description", "sql": "query_name", "explanation": "what this does"}}
2. For "sql" field, use ONLY the exact query name from the preloaded queries (stats, habit_changes, top_users, lesson_completion, recent_activity, screen_time_responses)
3. DO NOT generate custom SQL - only use the preloaded query names
4. DO NOT make up numbers or data - you must execute the actual query
5. For user count questions, use "stats"
6. For habit change questions, use "habit_changes"
7. For engagement questions, use "top_users"

Available Preloaded Queries:
- stats: Get current database statistics (users, lessons, activities, responses)
- lesson_completion_rates: Show engagement rates for each lesson in the course
- highest_lowest_completion: Which lessons have the highest and lowest engagement rates
- student_engagement_over_time: Show student engagement over time across the course
- incomplete_students: Which students have not finished the course yet
- average_completion_rate: Give me the average engagement rate across all lessons
- lesson_comparison: Compare engagement rates between specific lessons
- time_to_completion: Show how many students completed the course within 30 days of starting
- habit_changes: Get evidence of habit changes across lessons
- top_users: Get most engaged users
- recent_activity: Get recent user activity
- screen_time_responses: Get responses about screen time habits

EXAMPLE RESPONSES:
- "how many users" → {{"intent": "user_count", "sql": "stats", "explanation": "Get total user count from database"}}
- "show completion rates" → {{"intent": "completion_analysis", "sql": "lesson_completion_rates", "explanation": "Get completion rates for each lesson"}}
- "highest and lowest completion" → {{"intent": "completion_ranking", "sql": "highest_lowest_completion", "explanation": "Get lessons ranked by completion rate"}}
- "engagement over time" → {{"intent": "engagement_timeline", "sql": "student_engagement_over_time", "explanation": "Get engagement trends over time"}}
- "students not finished" → {{"intent": "incomplete_analysis", "sql": "incomplete_students", "explanation": "Get students who haven't completed the course"}}
- "average completion rate" → {{"intent": "completion_summary", "sql": "average_completion_rate", "explanation": "Get overall completion rate"}}
- "compare lesson 1 and 5" → {{"intent": "lesson_comparison", "sql": "lesson_comparison", "explanation": "Compare completion between lessons"}}
- "time to completion" → {{"intent": "completion_timing", "sql": "time_to_completion", "explanation": "Get completion timing analysis"}}
- "show habit changes" → {{"intent": "habit_analysis", "sql": "habit_changes", "explanation": "Get evidence of habit changes"}}
- "most engaged users" → {{"intent": "engagement_analysis", "sql": "top_users", "explanation": "Get most engaged users"}}
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
        valid_queries = ['stats', 'lesson_completion_rates', 'highest_lowest_completion', 'student_engagement_over_time', 'incomplete_students', 'average_completion_rate', 'lesson_comparison', 'time_to_completion', 'habit_changes', 'top_users', 'recent_activity', 'screen_time_responses', 'lesson_details', 'engagement_health', 'lesson_engagement', 'behavior_priorities', 'student_impact', 'unique_insights']
        if result.get('sql') not in valid_queries:
            # Force use of stats query if invalid
            result['sql'] = 'stats'
            result['intent'] = 'fallback_query'
            result['explanation'] = 'Using stats query as fallback'
        
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
        if 'completion' in intent.lower():
            if cleaned_results and 'completion_rate' in cleaned_results[0]:
                # Completion rates bar chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=[f"Lesson {r.get('lesson_number', i+1)}" for i, r in enumerate(cleaned_results)],
                        y=[r.get('completion_rate', 0) for r in cleaned_results],
                        name='Completion Rate (%)',
                        marker_color='#6366f1'
                    )
                ])
                fig.update_layout(
                    title='Lesson Completion Rates',
                    xaxis_title='Lesson',
                    yaxis_title='Completion Rate (%)',
                    template='plotly_white',
                    yaxis=dict(range=[0, 100])
                )
                return fig.to_json()
            elif cleaned_results and 'average_completion_rate' in cleaned_results[0]:
                # Single metric display
                avg_rate = cleaned_results[0].get('average_completion_rate', 0)
                fig = go.Figure(data=[
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=avg_rate,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': "Average Completion Rate (%)"},
                        gauge={'axis': {'range': [None, 100]},
                               'bar': {'color': "#6366f1"},
                               'steps': [{'range': [0, 50], 'color': "lightgray"},
                                        {'range': [50, 80], 'color': "yellow"},
                                        {'range': [80, 100], 'color': "green"}]}
                    )
                ])
                fig.update_layout(template='plotly_white')
                return fig.to_json()
        
        elif 'engagement' in intent.lower() or 'lesson' in intent.lower():
            if cleaned_results and 'lesson_number' in cleaned_results[0]:
                # Lesson engagement chart
                fig = go.Figure(data=[
                    go.Bar(
                        x=[r.get('lesson_number', r.get('lesson_name', f'Lesson {i}')) for i, r in enumerate(cleaned_results)],
                        y=[r.get('total_responses', r.get('users_reached', 0)) for r in cleaned_results],
                        name='Responses'
                    )
                ])
                fig.update_layout(
                    title='Lesson Engagement',
                    xaxis_title='Lesson',
                    yaxis_title='Responses',
                    template='plotly_white'
                )
                return fig.to_json()
        
        elif 'behavior' in intent.lower() or 'priority' in intent.lower():
            if 'behavior_category' in cleaned_results[0]:
                # Behavior priorities pie chart
                fig = go.Figure(data=[
                    go.Pie(
                        labels=[r.get('behavior_category', 'Other') for r in cleaned_results],
                        values=[r.get('mention_count', 0) for r in cleaned_results],
                        hole=0.3
                    )
                ])
                fig.update_layout(
                    title='Behavior Priorities',
                    template='plotly_white'
                )
                return fig.to_json()
        
        elif 'user' in intent.lower() or 'stats' in intent.lower():
            # Simple bar chart for user stats
            keys = list(cleaned_results[0].keys())
            numeric_keys = [k for k in keys if isinstance(cleaned_results[0][k], (int, float))]
            if numeric_keys:
                fig = go.Figure(data=[
                    go.Bar(
                        x=numeric_keys,
                        y=[cleaned_results[0][k] for k in numeric_keys],
                        name='Count'
                    )
                ])
                fig.update_layout(
                    title='Database Statistics',
                    xaxis_title='Metric',
                    yaxis_title='Count',
                    template='plotly_white'
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
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
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
                # Fallback to stats query
                query_sql = preloaded_queries['stats']['sql']
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

Available Queries: lesson_completion_rates, highest_lowest_completion, student_engagement_over_time, incomplete_students, average_completion_rate, lesson_comparison, time_to_completion, stats, habit_changes, top_users, recent_activity, screen_time_responses, lesson_details, engagement_health, lesson_engagement, behavior_priorities, student_impact, unique_insights

FORMATTING RULES:
1. ALWAYS put text summary ABOVE any visualization
2. Keep text concise but informative (2-4 sentences)
3. Use specific numbers and percentages from the data
4. For completion rates: "Lesson X has Y% completion rate"
5. For comparisons: "Lesson A (X%) vs Lesson B (Y%)"
6. For averages: "Average completion rate is X% across all lessons"
7. For incomplete students: "X students have not finished the course"
8. For engagement over time: "Peak engagement was X users on Y date"
9. Never use emojis - keep professional tone
10. If no data found, say "No completion data available for this query"

EXAMPLE RESPONSES:
- "Lesson 1 has the highest completion rate at 85%, while Lesson 5 is lowest at 45%."
- "Average completion rate across all lessons is 67%."
- "15 students have not finished the course yet, with 3-5 lessons remaining each."
- "Peak engagement was 12 users on August 18th, with steady decline since then."""
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
