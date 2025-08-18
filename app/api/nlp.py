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
import openai
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor

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
    """NLP service for translating natural language to SQL queries."""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.database_url = os.getenv("DATABASE_URL")
        
        # Initialize OpenAI client
        if self.openai_api_key:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None
            
        # Initialize database connection
        self.db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=self.database_url
        ) if self.database_url else None
        
        # Initialize LangChain (optional)
        self.chain = None
        if self.openai_api_key:
            try:
                llm = OpenAI(api_key=self.openai_api_key, temperature=0)
                prompt = PromptTemplate(
                    input_variables=["query", "query_type"],
                    template=SQL_TRANSLATION_PROMPT
                )
                self.chain = LLMChain(llm=llm, prompt=prompt)
                logger.info("LangChain initialized successfully")
            except Exception as e:
                logger.warning(f"LangChain initialization failed: {e}")
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
        
        # Updated schema patterns for unified data
        if "total" in query_lower and ("statement" in query_lower or "data" in query_lower):
            return """
            SELECT 
                source,
                COUNT(*) as total_statements,
                COUNT(DISTINCT actor_id) as unique_learners
            FROM statements_new
            GROUP BY source
            ORDER BY total_statements DESC
            """
        
        elif "focus group" in query_lower or "csv" in query_lower:
            return """
            SELECT 
                ce.extension_value as lesson_number,
                COUNT(*) as response_count,
                COUNT(DISTINCT s.actor_id) as unique_learners
            FROM statements_new s
            JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
            WHERE s.source = 'csv' 
                AND ce.extension_key = 'https://7taps.com/lesson-number'
            GROUP BY ce.extension_value
            ORDER BY lesson_number::integer
            """
        
        elif "xapi" in query_lower or "real-time" in query_lower:
            return """
            SELECT 
                verb_id,
                COUNT(*) as activity_count,
                COUNT(DISTINCT actor_id) as unique_learners
            FROM statements_new
            WHERE source = 'xapi'
            GROUP BY verb_id
            ORDER BY activity_count DESC
            """
        
        elif "learner" in query_lower and "engagement" in query_lower:
            return """
            SELECT 
                s.source,
                s.actor_id,
                COUNT(*) as total_activities,
                COUNT(DISTINCT s.activity_id) as unique_activities
            FROM statements_new s
            GROUP BY s.source, s.actor_id
            ORDER BY total_activities DESC
            LIMIT 20
            """
        
        elif "recent" in query_lower or "last" in query_lower:
            return """
            SELECT 
                s.source,
                s.actor_id,
                s.activity_id,
                s.verb_id,
                s.timestamp,
                r.response
            FROM statements_new s
            LEFT JOIN results_new r ON s.statement_id = r.statement_id
            ORDER BY s.timestamp DESC
            LIMIT 50
            """
        
        elif "card type" in query_lower or "response" in query_lower:
            return """
            SELECT 
                ce.extension_value as card_type,
                COUNT(*) as response_count,
                COUNT(DISTINCT s.actor_id) as unique_learners
            FROM statements_new s
            JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
            WHERE s.source = 'csv' 
                AND ce.extension_key = 'https://7taps.com/card-type'
            GROUP BY ce.extension_value
            ORDER BY response_count DESC
            """
        
        else:
            # Default query for general analytics
            return """
            SELECT 
                source,
                COUNT(*) as total_statements,
                COUNT(DISTINCT actor_id) as unique_learners,
                COUNT(DISTINCT activity_id) as unique_activities
            FROM statements_new
            GROUP BY source
            ORDER BY total_statements DESC
            """

    async def execute_sql_direct(self, sql: str) -> Dict[str, Any]:
        """Execute SQL query directly via database connection"""
        try:
            if not self.db_pool:
                return {"error": "Database connection not available"}
            
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    
                    # Convert to list of dicts
                    result_list = []
                    for row in results:
                        result_list.append(dict(row))
                    
                    return {
                        "results": result_list,
                        "row_count": len(result_list),
                        "success": True
                    }
                    
            finally:
                self.db_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to execute SQL directly: {e}")
            return {"error": f"Database error: {str(e)}"}

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
        results = await nlp_service.execute_sql_direct(translated_sql)
        
        # Step 3: Calculate confidence (simplified)
        confidence = 0.85 if nlp_service.chain else 0.65
        
        return {
            "query": request.query,
            "translated_sql": translated_sql,
            "results": results.get("results", []),
            "row_count": results.get("row_count", 0),
            "confidence": confidence,
            "database_url": nlp_service.database_url.split("@")[-1] if nlp_service.database_url else "not_configured",
            "message": f"Processed NLP query: {request.query}"
        }
        
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
        "database_url": nlp_service.database_url.split("@")[-1] if nlp_service.database_url else "not_configured",
        "capabilities": [
            "natural_language_to_sql",
            "unified_data_queries",
            "cross_source_analytics", 
            "focus_group_analysis",
            "xapi_activity_patterns",
            "learner_engagement_tracking",
            "response_quality_analysis"
        ],
        "schema": "normalized_relational",
        "data_sources": {
            "csv_focus_group": "373 statements",
            "xapi_real_time": "260 statements",
            "total_unified": "633 statements"
        },
        "langchain_status": "initialized" if nlp_service.chain is not None else "fallback_only",
        "example_queries": [
            "Show me the total number of statements from both xAPI and CSV sources",
            "What are the focus group responses by lesson?",
            "Show me recent activity from both data sources",
            "Which learners are most engaged across both sources?",
            "What are the card type distributions in the focus group data?"
        ]
    } 