from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import httpx
import json
import logging
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class NLPQueryRequest(BaseModel):
    query: str
    query_type: str = "analytics"  # cohort, completion, analytics, general

class NLPQueryResponse(BaseModel):
    original_query: str
    translated_sql: str
    results: Dict[str, Any]
    confidence: float
    error: Optional[str] = None

# SQL translation prompt template
SQL_TRANSLATION_PROMPT = """
You are a SQL expert. Translate the following natural language query into SQL for a PostgreSQL database.

Database schema:
- statements: stores xAPI statements with actor, verb, object, timestamp
- cohorts: stores user cohort information
- completions: stores completion tracking data

Rules:
1. Use only SELECT statements (read-only)
2. Include proper JOINs when needed
3. Use appropriate aggregation functions
4. Handle date/time filtering correctly
5. Return clean, executable SQL

Natural language query: {query}
Query type: {query_type}

Translate to SQL:
"""

class NLPService:
    def __init__(self):
        self.llm = None
        self.chain = None
        self.mcp_db_url = os.getenv("MCP_DB_URL", "http://localhost:8080")
        
        # Initialize LangChain if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.llm = OpenAI(api_key=api_key, temperature=0.1)
                prompt = PromptTemplate(
                    input_variables=["query", "query_type"],
                    template=SQL_TRANSLATION_PROMPT
                )
                self.chain = LLMChain(llm=self.llm, prompt=prompt)
                logger.info("LangChain initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize LangChain: {e}")
                self.chain = None
        else:
            logger.warning("OPENAI_API_KEY not found, using fallback SQL translation")
            self.chain = None

    async def translate_to_sql(self, query: str, query_type: str) -> str:
        """Translate natural language to SQL using LangChain or fallback"""
        
        if self.chain is not None:
            try:
                result = await self.chain.arun(query=query, query_type=query_type)
                return result.strip()
            except Exception as e:
                logger.error(f"LangChain translation failed: {e}")
                return self._fallback_translation(query, query_type)
        else:
            return self._fallback_translation(query, query_type)

    def _fallback_translation(self, query: str, query_type: str) -> str:
        """Fallback SQL translation for common query patterns"""
        query_lower = query.lower()
        
        # Common query patterns
        if "cohort" in query_lower and "completion" in query_lower:
            return """
            SELECT 
                c.cohort_name,
                COUNT(DISTINCT s.actor) as total_users,
                COUNT(DISTINCT CASE WHEN s.verb = 'completed' THEN s.actor END) as completed_users,
                ROUND(
                    COUNT(DISTINCT CASE WHEN s.verb = 'completed' THEN s.actor END) * 100.0 / 
                    COUNT(DISTINCT s.actor), 2
                ) as completion_rate
            FROM statements s
            LEFT JOIN cohorts c ON s.actor = c.user_id
            WHERE c.cohort_name IS NOT NULL
            GROUP BY c.cohort_name
            ORDER BY completion_rate DESC
            """
        
        elif "completion rate" in query_lower:
            return """
            SELECT 
                DATE_TRUNC('day', timestamp) as date,
                COUNT(DISTINCT actor) as total_users,
                COUNT(DISTINCT CASE WHEN verb = 'completed' THEN actor END) as completed_users,
                ROUND(
                    COUNT(DISTINCT CASE WHEN verb = 'completed' THEN actor END) * 100.0 / 
                    COUNT(DISTINCT actor), 2
                ) as completion_rate
            FROM statements
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY DATE_TRUNC('day', timestamp)
            ORDER BY date DESC
            """
        
        elif "recent activity" in query_lower or "last" in query_lower:
            return """
            SELECT 
                actor,
                verb,
                object,
                timestamp
            FROM statements
            ORDER BY timestamp DESC
            LIMIT 50
            """
        
        elif "user engagement" in query_lower:
            return """
            SELECT 
                actor,
                COUNT(*) as statement_count,
                COUNT(DISTINCT DATE(timestamp)) as active_days,
                MAX(timestamp) as last_activity
            FROM statements
            GROUP BY actor
            ORDER BY statement_count DESC
            LIMIT 20
            """
        
        else:
            # Default query for general analytics
            return """
            SELECT 
                verb,
                COUNT(*) as count,
                COUNT(DISTINCT actor) as unique_users
            FROM statements
            WHERE timestamp >= NOW() - INTERVAL '7 days'
            GROUP BY verb
            ORDER BY count DESC
            """

    async def execute_sql_via_mcp(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query via MCP DB server"""
        try:
            async with httpx.AsyncClient() as client:
                # MCP DB server endpoint for SQL execution
                response = await client.post(
                    f"{self.mcp_db_url}/sql",
                    json={"query": sql},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"MCP DB error: {response.status_code} - {response.text}")
                    return {"error": f"MCP DB error: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to execute SQL via MCP: {e}")
            return {"error": f"SQL execution failed: {str(e)}"}

# Initialize NLP service
nlp_service = NLPService()

@router.post("/ui/nlp-query", response_model=NLPQueryResponse)
async def nlp_query(request: NLPQueryRequest):
    """
    Translate natural language query to SQL and execute via MCP DB
    """
    try:
        logger.info(f"Processing NLP query: {request.query} (type: {request.query_type})")
        
        # Step 1: Translate natural language to SQL
        translated_sql = await nlp_service.translate_to_sql(request.query, request.query_type)
        logger.info(f"Translated SQL: {translated_sql}")
        
        # Step 2: Execute SQL via MCP DB
        results = await nlp_service.execute_sql_via_mcp(translated_sql)
        
        # Step 3: Calculate confidence (simplified)
        confidence = 0.85 if nlp_service.chain else 0.65
        
        return NLPQueryResponse(
            original_query=request.query,
            translated_sql=translated_sql,
            results=results,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"NLP query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"NLP query processing failed: {str(e)}"
        )

@router.get("/ui/nlp-status")
async def nlp_status():
    """Check NLP service status and capabilities"""
    return {
        "status": "healthy",
        "langchain_available": nlp_service.chain is not None,
        "mcp_db_url": nlp_service.mcp_db_url,
        "capabilities": [
            "natural_language_to_sql",
            "cohort_analysis", 
            "completion_tracking",
            "user_engagement",
            "recent_activity"
        ],
        "langchain_status": "initialized" if nlp_service.chain is not None else "fallback_only"
    } 