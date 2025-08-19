from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
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

def execute_query(sql_query):
    """Execute a SQL query and return results"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            results = cur.fetchall()
            return [dict(row) for row in results]
    finally:
        conn.close()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat requests from the HTML interface"""
    
    try:
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Prepare conversation history
        messages = [
            {
                "role": "system",
                "content": """You are Seven, an AI analytics assistant. Give simple, clear, concise answers.

IMPORTANT: When asked about data, ALWAYS query the database and provide actual numbers and insights. Don't give generic responses.

Data sources:
- statements_new: Learning activity data
- context_extensions_new: Metadata (lesson numbers, card types)
- results_new: Learner responses

When asked for analytics, run SQL queries and return specific data with numbers. Be direct and actionable."""
            }
        ]
        
        # Add conversation history (limit to last 10 messages to avoid token limits)
        for msg in request.history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Check if this is a data query request
        data_keywords = ['data', 'statistics', 'numbers', 'count', 'how many', 'engagement', 'progress', 'cohort', 'users', 'lessons', 'statements']
        is_data_query = any(keyword in request.message.lower() for keyword in data_keywords)
        
        if is_data_query:
            # Get some basic data to provide context
            try:
                # Get basic stats
                total_statements = execute_query("SELECT COUNT(*) as count FROM statements_new")[0]['count']
                unique_users = execute_query("SELECT COUNT(DISTINCT actor_id) as count FROM statements_new")[0]['count']
                total_lessons = execute_query("SELECT COUNT(DISTINCT lesson_number) as count FROM context_extensions_new WHERE lesson_number IS NOT NULL")[0]['count']
                
                # Add data context to the message
                data_context = f"\n\nCurrent data: {total_statements} statements, {unique_users} users, {total_lessons} lessons."
                messages[-1]["content"] += data_context
                
                # For specific queries, run actual SQL
                if 'engagement' in request.message.lower():
                    engagement_data = execute_query("""
                        SELECT ce.lesson_number, COUNT(*) as interactions
                        FROM statements_new s
                        JOIN context_extensions_new ce ON s.id = ce.statement_id
                        WHERE ce.lesson_number IS NOT NULL
                        GROUP BY ce.lesson_number
                        ORDER BY ce.lesson_number
                    """)
                    messages[-1]["content"] += f"\nEngagement data: {engagement_data}"
                
                elif 'cohort' in request.message.lower():
                    cohort_data = execute_query("""
                        SELECT 
                            CASE 
                                WHEN interaction_count >= 50 THEN 'High Activity'
                                WHEN interaction_count >= 20 THEN 'Medium Activity'
                                ELSE 'Low Activity'
                            END as cohort,
                            COUNT(*) as user_count
                        FROM (
                            SELECT actor_id, COUNT(*) as interaction_count
                            FROM statements_new
                            GROUP BY actor_id
                        ) user_stats
                        GROUP BY cohort
                    """)
                    messages[-1]["content"] += f"\nCohort data: {cohort_data}"
                
            except Exception as e:
                messages[-1]["content"] += f"\nNote: Could not fetch data due to error: {str(e)}"
        
        # Generate response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return ChatResponse(response=response.choices[0].message.content)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/chat/health")
async def chat_health():
    """Health check for chat service"""
    return {"status": "healthy", "service": "chat"}
