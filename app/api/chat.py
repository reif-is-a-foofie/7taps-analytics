from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

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
                    COUNT(DISTINCT ur.user_id) as users_responded,
                    CASE 
                        WHEN COUNT(DISTINCT ua.user_id) > 0 
                        THEN ROUND(COUNT(DISTINCT ur.user_id) * 100.0 / COUNT(DISTINCT ua.user_id), 1)
                        ELSE 0
                    END as completion_rate
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
                    COUNT(ua.id) as total_activities,
                    COUNT(ur.id) as total_responses,
                    COUNT(DISTINCT ua.user_id) as unique_users,
                    ROUND(AVG(LENGTH(ur.response_text)), 1) as avg_response_length
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
                    ROUND(COUNT(CASE WHEN ur.response_text ILIKE '%improve%' OR ur.response_text ILIKE '%better%' THEN 1 END) * 100.0 / COUNT(ur.id), 1) as improvement_rate
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
- habit_changes: Get evidence of habit changes across lessons
- top_users: Get most engaged users
- lesson_completion: Get lesson completion rates
- recent_activity: Get recent user activity
- screen_time_responses: Get responses about screen time habits

EXAMPLE RESPONSES:
- "how many users" → {{"intent": "user_count", "sql": "stats", "explanation": "Get total user count from database"}}
- "show habit changes" → {{"intent": "habit_analysis", "sql": "habit_changes", "explanation": "Get evidence of habit changes"}}
- "most engaged users" → {{"intent": "engagement_analysis", "sql": "top_users", "explanation": "Get most engaged users"}}
- "first lesson details" → {{"intent": "lesson_analysis", "sql": "lesson_details", "explanation": "Get first lesson with questions and responses"}}
- "engagement health" → {{"intent": "engagement_analysis", "sql": "engagement_health", "explanation": "Get completion rates and drop-off analysis"}}
- "which lessons are most engaging" → {{"intent": "lesson_analysis", "sql": "lesson_engagement", "explanation": "Get lesson engagement rankings"}}
- "what behaviors matter most" → {{"intent": "behavior_analysis", "sql": "behavior_priorities", "explanation": "Get behavior priority analysis"}}
- "did students change behavior" → {{"intent": "impact_analysis", "sql": "student_impact", "explanation": "Get student behavior change evidence"}}
- "unique student insights" → {{"intent": "insight_analysis", "sql": "unique_insights", "explanation": "Get vulnerable student reflections"}}
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
        valid_queries = ['stats', 'habit_changes', 'top_users', 'lesson_completion', 'recent_activity', 'screen_time_responses', 'lesson_details', 'engagement_health', 'lesson_engagement', 'behavior_priorities', 'student_impact', 'unique_insights']
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
        if 'engagement' in intent.lower() or 'lesson' in intent.lower():
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

@router.post("/chat", response_model=ChatResponse)
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
            if llm_result['sql'] in preloaded_queries:
                # Use preloaded query
                query_sql = preloaded_queries[llm_result['sql']]['sql']
                query_results = execute_query(query_sql)
                data_summary = format_query_results(query_results, llm_result['intent'])
            else:
                # Execute custom SQL
                query_results = execute_query(llm_result['sql'])
                data_summary = format_query_results(query_results, llm_result['intent'])
        except Exception as e:
            data_summary = f"Query failed: {str(e)}"
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
                "content": f"""You are Seven, an AI analytics assistant. Give concise, data-driven answers.

Database Schema:
{json.dumps(schema_summary, indent=2)}

Available Queries: stats, habit_changes, top_users, lesson_completion, recent_activity, screen_time_responses, lesson_details, engagement_health, lesson_engagement, behavior_priorities, student_impact, unique_insights

        Instructions:
        - Keep responses under 100 words
        - Be specific with numbers and examples
        - Use the query results provided to answer questions
        - Reference the schema above to understand available data
        - Never use emojis in responses
        - Keep responses professional and data-focused"""
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
