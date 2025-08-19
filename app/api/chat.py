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
                AND table_name IN ('statements_new', 'results_new', 'context_extensions_new')
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

def get_sample_data():
    """Get sample data from each table for context"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get sample data from each table
            samples = {}
            
            # Sample statements
            cur.execute("SELECT * FROM statements_new LIMIT 3")
            statements = []
            for row in cur.fetchall():
                row_dict = dict(row)
                # Convert datetime objects to strings
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                statements.append(row_dict)
            samples['statements_new'] = statements
            
            # Sample results
            cur.execute("SELECT * FROM results_new LIMIT 3")
            results = []
            for row in cur.fetchall():
                row_dict = dict(row)
                # Convert datetime objects to strings
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                results.append(row_dict)
            samples['results_new'] = results
            
            # Sample context extensions
            cur.execute("SELECT * FROM context_extensions_new LIMIT 3")
            extensions = []
            for row in cur.fetchall():
                row_dict = dict(row)
                # Convert datetime objects to strings
                for key, value in row_dict.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                extensions.append(row_dict)
            samples['context_extensions_new'] = extensions
            
            return samples
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
    
    # Create context with schema and sample data
    context = f"""
Database Schema:
{json.dumps(schema, indent=2)}

Sample Data:
{json.dumps(sample_data, indent=2)}

User Question: {user_message}

Instructions:
1. Analyze the user's intent
2. Generate appropriate SQL query (ONLY SELECT statements)
3. Return JSON with: {{"intent": "description", "sql": "SELECT query", "explanation": "what this query does"}}

Rules:
- Only generate SELECT queries
- Use proper JOINs between tables
- Include LIMIT clauses for large result sets
- Focus on the specific intent of the user
- Note: lesson information is stored in context_extensions_new.extension_key = 'lesson_number' and context_extensions_new.extension_value contains the lesson number
- Note: card information is stored in context_extensions_new.extension_key = 'card_number' and context_extensions_new.extension_value contains the card number
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
            "sql": "SELECT COUNT(*) as total FROM statements_new",
            "explanation": "Basic count query as fallback"
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
        
        # Get database context
        schema = get_database_schema()
        sample_data = get_sample_data()
        
        # Get basic stats for context - fix the queries to work with actual schema
        total_statements = execute_query("SELECT COUNT(*) as count FROM statements_new")[0]['count']
        unique_users = execute_query("SELECT COUNT(DISTINCT actor_id) as count FROM statements_new")[0]['count']
        
        # Fix lesson count query - lesson_number is stored in extension_key/extension_value
        lesson_count_result = execute_query("""
            SELECT COUNT(DISTINCT extension_value) as count 
            FROM context_extensions_new 
            WHERE extension_key = 'lesson_number'
        """)
        total_lessons = lesson_count_result[0]['count'] if lesson_count_result else 0
        
        # Use LLM to determine intent and generate SQL
        llm_result = get_llm_intent_and_sql(request.message, schema, sample_data)
        
        # Execute the generated SQL
        try:
            query_results = execute_query(llm_result['sql'])
            data_summary = format_query_results(query_results, llm_result['intent'])
        except Exception as e:
            data_summary = f"Query failed: {str(e)}"
            query_results = []
        
        # Prepare conversation history with full context
        messages = [
            {
                "role": "system",
                "content": f"""You are Seven, an AI analytics assistant. Give simple, clear, concise answers.

Current Database Stats:
- {total_statements} total statements
- {unique_users} unique users  
- {total_lessons} lessons

Database Schema:
{json.dumps(schema, indent=2)}

Sample Data:
{json.dumps(sample_data, indent=2)}

Instructions:
- Always provide specific data and numbers
- Be concise and actionable
- If data is available, use it
- If no data, say so clearly
- Keep responses under 200 words
- Note: lesson information is stored in context_extensions_new.extension_key = 'lesson_number' and context_extensions_new.extension_value contains the lesson number"""
            }
        ]
        
        # Add conversation history (keep full context)
        for msg in request.history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message with query results
        current_message = f"""
User: {request.message}

Intent: {llm_result['intent']}
SQL Generated: {llm_result['sql']}
Query Results: {data_summary}

Please provide a clear, concise response based on this data."""
        
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
