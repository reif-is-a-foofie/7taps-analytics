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

def get_preloaded_data():
    """Get comprehensive preloaded data for context"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            data = {}
            
            # Key statistics
            cur.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM statements_new) as total_statements,
                    (SELECT COUNT(*) FROM users) as total_users,
                    (SELECT COUNT(*) FROM lessons) as total_lessons,
                    (SELECT COUNT(*) FROM user_responses) as total_responses,
                    (SELECT COUNT(*) FROM user_activities) as total_activities
            """)
            stats = cur.fetchone()
            data['stats'] = dict(stats)
            
            # All lessons with names
            cur.execute("SELECT lesson_number, lesson_name FROM lessons ORDER BY lesson_number")
            data['lessons'] = [dict(row) for row in cur.fetchall()]
            
            # Top users by activity
            cur.execute("""
                SELECT u.user_id, COUNT(ua.id) as activity_count, 
                       MIN(ua.timestamp) as first_activity, MAX(ua.timestamp) as last_activity
                FROM users u 
                LEFT JOIN user_activities ua ON u.id = ua.user_id 
                GROUP BY u.id, u.user_id 
                ORDER BY activity_count DESC 
                LIMIT 10
            """)
            data['top_users'] = [dict(row) for row in cur.fetchall()]
            
            # Key habit change responses (most meaningful)
            cur.execute("""
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
            """)
            data['habit_responses'] = [dict(row) for row in cur.fetchall()]
            
            # Lesson completion rates
            cur.execute("""
                SELECT l.lesson_number, l.lesson_name, COUNT(DISTINCT ua.user_id) as users_completed
                FROM lessons l 
                LEFT JOIN user_activities ua ON l.id = ua.lesson_id 
                GROUP BY l.id, l.lesson_number, l.lesson_name 
                ORDER BY l.lesson_number
            """)
            data['lesson_completion'] = [dict(row) for row in cur.fetchall()]
            
            return data
    finally:
        conn.close()

def execute_query(sql_query):
    """Execute a SQL query and return results"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            results = cur.fetchall()
            return [dict(row) for row in results]
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")
    finally:
        conn.close()

def get_llm_intent_and_sql(user_message: str, schema: Dict, sample_data: Dict) -> Dict[str, Any]:
    """Use LLM to determine intent and generate SQL"""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Create context with schema and preloaded data
    context = f"""
Database Schema:
{json.dumps(schema, indent=2)}

Preloaded Data Available:
{json.dumps(sample_data, indent=2)}

User Question: {user_message}

Instructions:
1. Analyze the user's intent
2. If data is in preloaded_data, use it instead of SQL
3. Only generate SQL if absolutely necessary
4. Return JSON with: {{"intent": "description", "sql": "SELECT query or 'use_preloaded'", "explanation": "what this does"}}

Rules:
- Prefer preloaded data over SQL queries
- For habit changes, use habit_responses data
- For user stats, use top_users data
- For lesson info, use lessons data
- Only generate SQL if specific data not in preloaded_data
"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a SQL expert. Generate only SELECT queries. Return valid JSON."},
            {"role": "user", "content": context}
        ],
        max_tokens=500,
        temperature=0.1
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        return result
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "intent": "general_query",
            "sql": "use_preloaded",
            "explanation": "Use preloaded data for general queries"
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
        
        # Get preloaded data (comprehensive context)
        preloaded_data = get_preloaded_data()
        schema = get_database_schema()
        
        # Use LLM to determine intent and generate SQL
        llm_result = get_llm_intent_and_sql(request.message, schema, preloaded_data)
        
        # Execute the generated SQL or use preloaded data
        try:
            if llm_result['sql'] == 'use_preloaded':
                data_summary = "Using preloaded data"
                query_results = []
            else:
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

PRELOADED DATA (use this instead of making queries):
{json.dumps(preloaded_data, indent=2)}

Database Schema:
{json.dumps(schema, indent=2)}

KEY INSIGHTS (pre-analyzed):
- {preloaded_data['stats']['total_users']} users across {preloaded_data['stats']['total_lessons']} lessons
- {preloaded_data['stats']['total_responses']} meaningful responses analyzed
- Top users: {', '.join([u['user_id'] for u in preloaded_data['top_users'][:3]])}
- Key habit changes found in responses (see habit_responses data)

Instructions:
- Use preloaded data - don't make new queries unless absolutely necessary
- Keep responses under 100 words
- Be specific with numbers and examples
- For habit changes, reference the habit_responses data
- If user asks for specific analysis, use the preloaded data first"""
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
