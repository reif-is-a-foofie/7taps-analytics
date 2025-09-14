"""
Chat service for AI-powered analytics queries.
"""
from typing import Dict, Any, List, Optional
import structlog
import json
from datetime import datetime

from app.core.exceptions import ExternalServiceError, ValidationError
from app.database import execute_query
from app.redis_client import get_redis_client

logger = structlog.get_logger()


class ChatService:
    """Service for handling AI chat functionality."""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.openai_client = None
        
    async def initialize_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.openai_client = openai.OpenAI()
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize OpenAI client", error=str(e))
            raise ExternalServiceError(f"OpenAI initialization failed: {str(e)}")
    
    async def process_chat_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a chat message and return AI response."""
        try:
            if not self.openai_client:
                await self.initialize_openai()
            
            # Get database schema and sample data for context
            schema = await self.get_database_schema()
            sample_data = await self.get_sample_data()
            
            # Create context for LLM
            llm_context = {
                "message": message,
                "schema": schema,
                "sample_data": sample_data,
                "context": context or {}
            }
            
            # Use LLM to determine intent and generate response
            response = await self.generate_llm_response(llm_context)
            
            return {
                "success": True,
                "response": response["text"],
                "intent": response.get("intent"),
                "confidence": response.get("confidence", 0.8),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Chat message processing failed", error=str(e))
            raise ExternalServiceError(f"Chat processing failed: {str(e)}")
    
    async def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information."""
        try:
            # Get table information
            tables_query = """
            SELECT table_name, column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
            
            results = execute_query(tables_query)
            
            # Organize by table
            schema = {}
            for row in results:
                table_name = row["table_name"]
                if table_name not in schema:
                    schema[table_name] = {"columns": []}
                
                schema[table_name]["columns"].append({
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES"
                })
            
            return schema
            
        except Exception as e:
            logger.error("Failed to get database schema", error=str(e))
            return {}
    
    async def get_sample_data(self) -> Dict[str, Any]:
        """Get sample data from key tables."""
        try:
            sample_data = {}
            
            # Get sample from key tables
            tables = ["xapi_statements", "users", "lessons"]
            for table in tables:
                try:
                    query = f"SELECT * FROM {table} LIMIT 5"
                    results = execute_query(query)
                    sample_data[table] = results
                except Exception as e:
                    logger.warning(f"Failed to get sample data from {table}", error=str(e))
                    sample_data[table] = []
            
            return sample_data
            
        except Exception as e:
            logger.error("Failed to get sample data", error=str(e))
            return {}
    
    async def generate_llm_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM response based on context."""
        try:
            if not self.openai_client:
                await self.initialize_openai()
            
            # Create prompt for LLM
            prompt = f"""
            You are an AI assistant for 7taps Analytics. Help users understand their learning data.
            
            User Question: {context['message']}
            
            Database Schema: {json.dumps(context['schema'], indent=2)}
            Sample Data: {json.dumps(context['sample_data'], indent=2)}
            
            Provide a helpful response about the data. If the user asks for specific metrics,
            suggest appropriate queries or provide insights based on the available data.
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful analytics assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return {
                "text": response.choices[0].message.content,
                "intent": "analytics_query",
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error("LLM response generation failed", error=str(e))
            return {
                "text": "I'm sorry, I'm having trouble processing your request right now. Please try again later.",
                "intent": "error",
                "confidence": 0.0
            }
    
    async def get_chat_history(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get chat history for a user."""
        try:
            if not self.redis_client:
                return []
            
            # Get chat history from Redis
            key = f"chat_history:{user_id or 'default'}"
            history = self.redis_client.lrange(key, 0, 49)  # Last 50 messages
            
            return [json.loads(msg) for msg in history if msg]
            
        except Exception as e:
            logger.error("Failed to get chat history", error=str(e))
            return []
    
    async def save_chat_message(self, message: str, response: str, user_id: Optional[str] = None):
        """Save chat message and response to history."""
        try:
            if not self.redis_client:
                return
            
            # Save to Redis
            key = f"chat_history:{user_id or 'default'}"
            chat_entry = {
                "message": message,
                "response": response,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            }
            
            self.redis_client.lpush(key, json.dumps(chat_entry))
            self.redis_client.ltrim(key, 0, 99)  # Keep last 100 messages
            
        except Exception as e:
            logger.error("Failed to save chat message", error=str(e))

