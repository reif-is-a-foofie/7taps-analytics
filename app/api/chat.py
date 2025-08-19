from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import openai
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

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
                AND table_name IN ('statements_new', 'results_new', 'context_extensions_new', 'lessons', 'users', 'questions', 'user_activities', 'user_responses')
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
        valid_queries = ['stats', 'habit_changes', 'top_users', 'lesson_completion', 'recent_activity', 'screen_time_responses']
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
        
        # Prepare conversation history with full context
        messages = [
            {
                "role": "system",
                "content": f"""You are Seven, an AI analytics assistant. Give concise, data-driven answers.

PRELOADED QUERIES (use these for live data):
{json.dumps(preloaded_queries, indent=2)}

Database Schema:
{json.dumps(schema, indent=2)}

Instructions:
- Use preloaded query names (stats, habit_changes, top_users, etc.) when they match the intent
- Always execute fresh queries for live data - never use stale data
- Keep responses under 100 words
- Be specific with numbers and examples
- For habit changes, use the habit_changes query
- For user engagement, use the top_users query
- For recent activity, use the recent_activity query"""
            }
        ]
        
        # Add conversation history (keep full context)
        for msg in request.history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message with context accumulation
        current_message = f"""
User: {request.message}

Intent: {llm_result['intent']}
SQL Generated: {llm_result['sql']}
Query Results: {data_summary}

Previous Context: {len(request.history)} messages in conversation
Preloaded Data Available: Yes (use habit_responses, lesson_completion, top_users)

Please provide a concise response using the preloaded data."""
        
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
        
        return ChatResponse(response=response.choices[0].message.content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/chat/health")
async def chat_health():
    """Health check for chat service"""
    return {"status": "healthy", "service": "chat"}
