"""
Public API Router - External-facing endpoints for data consumers only.
This router exposes a clean, minimal API surface for external data access.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from pydantic import BaseModel, Field

router = APIRouter(tags=["Public Data API"])

# Composable Sub-App Contract Models
class APIDocsActionRequest(BaseModel):
    action: str = Field(..., description="Action to perform: list_endpoints, get_schema, get_examples")
    endpoint: Optional[str] = Field(None, description="Endpoint name for get_schema and get_examples actions")

class APIDocsActionResponse(BaseModel):
    success: bool = Field(..., description="Whether the action was successful")
    action: str = Field(..., description="The action that was performed")
    endpoints: Optional[List[Dict[str, Any]]] = Field(None, description="List of endpoints for list_endpoints action")
    categories: Optional[List[str]] = Field(None, description="Endpoint categories for list_endpoints action")
    schema_data: Optional[Dict[str, Any]] = Field(None, description="Schema for get_schema action")
    parameters: Optional[List[Dict[str, Any]]] = Field(None, description="Parameters for get_schema action")
    responses: Optional[Dict[str, Any]] = Field(None, description="Responses for get_schema action")
    examples: Optional[List[Dict[str, Any]]] = Field(None, description="Examples for get_examples action")
    curl_commands: Optional[List[str]] = Field(None, description="cURL commands for get_examples action")
    error: Optional[str] = Field(None, description="Error message if action failed")

def get_db_connection():
    """Get database connection"""
    # Disabled - using BigQuery instead of PostgreSQL
    raise HTTPException(status_code=501, detail="PostgreSQL routes disabled - using BigQuery instead")

@router.get("/data/schema", summary="Get database schema")
async def get_schema():
    """
    Get the current database schema for the analytics data.
    Returns table structures and relationships for data consumers.
    """
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
            
            return {
                "schema": schema,
                "description": "Normalized analytics data schema",
                "tables": {
                    "statements_new": "Main learning activity statements",
                    "results_new": "Learner responses and outcomes", 
                    "context_extensions_new": "Metadata and context information"
                }
            }
    finally:
        conn.close()

@router.post("/data/query", summary="Execute a data query")
async def execute_query(query: Dict[str, str]):
    """
    Execute a SQL query against the analytics data.
    
    **Security Note**: Only SELECT queries are allowed.
    """
    sql_query = query.get("query", "").strip()
    
    if not sql_query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    # Security: Only allow SELECT queries
    if not sql_query.upper().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql_query)
            results = cur.fetchall()
            
            return {
                "query": sql_query,
                "results": [dict(row) for row in results],
                "count": len(results),
                "executed_at": datetime.utcnow().isoformat()
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")
    finally:
        conn.close()

@router.get("/data/sample-queries", summary="Get sample queries")
async def get_sample_queries():
    """
    Get sample queries that demonstrate common data access patterns.
    """
    return {
        "sample_queries": [
            {
                "name": "User Engagement by Lesson",
                "description": "Show how many interactions each user had per lesson",
                "query": """
                    SELECT 
                        s.actor_id,
                        ce.lesson_number,
                        COUNT(*) as interactions
                    FROM statements_new s
                    JOIN context_extensions_new ce ON s.id = ce.statement_id
                    WHERE ce.lesson_number IS NOT NULL
                    GROUP BY s.actor_id, ce.lesson_number
                    ORDER BY s.actor_id, ce.lesson_number
                """
            },
            {
                "name": "Most Active Users",
                "description": "Find users with the highest engagement",
                "query": """
                    SELECT 
                        actor_id,
                        COUNT(*) as total_interactions
                    FROM statements_new
                    GROUP BY actor_id
                    ORDER BY total_interactions DESC
                    LIMIT 10
                """
            },
            {
                "name": "Lesson Completion Rates",
                "description": "Calculate completion rates for each lesson",
                "query": """
                    SELECT 
                        ce.lesson_number,
                        COUNT(DISTINCT s.actor_id) as unique_users,
                        COUNT(*) as total_interactions
                    FROM statements_new s
                    JOIN context_extensions_new ce ON s.id = ce.statement_id
                    WHERE ce.lesson_number IS NOT NULL
                    GROUP BY ce.lesson_number
                    ORDER BY ce.lesson_number
                """
            },
            {
                "name": "Recent Activity",
                "description": "Show recent learning activity",
                "query": """
                    SELECT 
                        s.actor_id,
                        s.timestamp,
                        s.verb,
                        ce.lesson_number
                    FROM statements_new s
                    LEFT JOIN context_extensions_new ce ON s.id = ce.statement_id
                    ORDER BY s.timestamp DESC
                    LIMIT 20
                """
            }
        ]
    }

@router.get("/data/status", summary="Get data status")
async def get_data_status():
    """
    Get current status and statistics of the analytics data.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get total statements
            cur.execute("SELECT COUNT(*) as count FROM statements_new")
            total_statements = cur.fetchone()['count']
            
            # Get unique users
            cur.execute("SELECT COUNT(DISTINCT actor_id) as count FROM statements_new")
            unique_users = cur.fetchone()['count']
            
            # Get total lessons
            cur.execute("SELECT COUNT(DISTINCT lesson_number) as count FROM context_extensions_new WHERE lesson_number IS NOT NULL")
            total_lessons = cur.fetchone()['count']
            
            # Get latest activity
            cur.execute("SELECT MAX(timestamp) as latest FROM statements_new")
            latest_activity = cur.fetchone()['latest']
            
            return {
                "status": "healthy",
                "total_statements": total_statements,
                "unique_users": unique_users,
                "total_lessons": total_lessons,
                "latest_activity": latest_activity.isoformat() if latest_activity else None,
                "last_updated": datetime.utcnow().isoformat()
            }
    finally:
        conn.close()

@router.get("/analytics/cohorts", summary="Get cohort analytics")
async def get_cohort_analytics():
    """
    Get analytics data grouped by user cohorts.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get cohort data (grouping users by activity level)
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN interaction_count >= 50 THEN 'High Activity'
                        WHEN interaction_count >= 20 THEN 'Medium Activity'
                        ELSE 'Low Activity'
                    END as cohort,
                    COUNT(*) as user_count,
                    AVG(interaction_count) as avg_interactions
                FROM (
                    SELECT 
                        actor_id,
                        COUNT(*) as interaction_count
                    FROM statements_new
                    GROUP BY actor_id
                ) user_stats
                GROUP BY cohort
                ORDER BY avg_interactions DESC
            """)
            
            cohorts = [dict(row) for row in cur.fetchall()]
            
            return {
                "cohorts": cohorts,
                "total_cohorts": len(cohorts),
                "generated_at": datetime.utcnow().isoformat()
            }
    finally:
        conn.close()

@router.get("/analytics/cohorts/{cohort_id}", summary="Get specific cohort details")
async def get_cohort_details(cohort_id: str):
    """
    Get detailed analytics for a specific cohort.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get users in this cohort
            cur.execute("""
                SELECT 
                    actor_id,
                    COUNT(*) as interaction_count,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity
                FROM statements_new
                GROUP BY actor_id
                HAVING 
                    CASE 
                        WHEN %s = 'high' THEN COUNT(*) >= 50
                        WHEN %s = 'medium' THEN COUNT(*) >= 20 AND COUNT(*) < 50
                        WHEN %s = 'low' THEN COUNT(*) < 20
                        ELSE FALSE
                    END
                ORDER BY interaction_count DESC
            """, (cohort_id, cohort_id, cohort_id))
            
            users = [dict(row) for row in cur.fetchall()]
            
            return {
                "cohort_id": cohort_id,
                "user_count": len(users),
                "users": users,
                "generated_at": datetime.utcnow().isoformat()
            }
    finally:
        conn.close()

# Health endpoint removed - use /api/health from health.py instead

# Composable Sub-App Contract Endpoints for APIDocs
@router.post("/docs/list-endpoints",
    response_model=APIDocsActionResponse,
    summary="APIDocs.list_endpoints action",
    description="List all available API endpoints organized by category"
)
async def api_docs_list_endpoints(request: APIDocsActionRequest):
    """APIDocs.list_endpoints action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "list_endpoints":
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'list_endpoints'"
            )
        
        # Define available endpoints organized by category
        endpoints = [
            {
                "path": "/api/data/schema",
                "method": "GET",
                "category": "Data Access",
                "description": "Get database schema information",
                "tags": ["schema", "metadata"]
            },
            {
                "path": "/api/data/query",
                "method": "POST", 
                "category": "Data Access",
                "description": "Execute SQL queries against analytics data",
                "tags": ["query", "sql"]
            },
            {
                "path": "/api/data/sample-queries",
                "method": "GET",
                "category": "Data Access", 
                "description": "Get sample queries for common patterns",
                "tags": ["examples", "templates"]
            },
            {
                "path": "/api/data/status",
                "method": "GET",
                "category": "Monitoring",
                "description": "Get current data status and statistics",
                "tags": ["status", "health"]
            },
            {
                "path": "/api/analytics/cohorts",
                "method": "GET",
                "category": "Analytics",
                "description": "Get cohort analytics data",
                "tags": ["cohorts", "analytics"]
            },
            {
                "path": "/api/analytics/cohorts/{cohort_id}",
                "method": "GET",
                "category": "Analytics",
                "description": "Get detailed analytics for specific cohort",
                "tags": ["cohorts", "details"]
            },
            {
                "path": "/api/health",
                "method": "GET",
                "category": "Monitoring",
                "description": "Health check endpoint",
                "tags": ["health", "status"]
            }
        ]
        
        categories = list(set([ep["category"] for ep in endpoints]))
        
        return APIDocsActionResponse(
            success=True,
            action=request.action,
            endpoints=endpoints,
            categories=categories
        )
        
    except Exception as e:
        return APIDocsActionResponse(
            success=False,
            action=request.action,
            error=f"Action failed: {str(e)}"
        )

@router.post("/docs/get-schema",
    response_model=APIDocsActionResponse,
    summary="APIDocs.get_schema action", 
    description="Get detailed schema information for a specific endpoint"
)
async def api_docs_get_schema(request: APIDocsActionRequest):
    """APIDocs.get_schema action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "get_schema":
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'get_schema'"
            )
        
        if not request.endpoint:
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error="Endpoint parameter is required for get_schema action"
            )
        
        # Define schemas for different endpoints
        schemas = {
            "/api/data/schema": {
                "description": "Get database schema information",
                "method": "GET",
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "Successfully retrieved schema",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "schema": {"type": "object"},
                                        "description": {"type": "string"},
                                        "tables": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/data/query": {
                "description": "Execute SQL query",
                "method": "POST",
                "parameters": [
                    {
                        "name": "query",
                        "type": "object",
                        "required": True,
                        "description": "Query object containing SQL string"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Query executed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "results": {"type": "array"},
                                        "count": {"type": "integer"},
                                        "executed_at": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {
                        "description": "Invalid query or execution error"
                    }
                }
            },
            "/api/analytics/cohorts": {
                "description": "Get cohort analytics",
                "method": "GET", 
                "parameters": [],
                "responses": {
                    "200": {
                        "description": "Cohort data retrieved successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "cohorts": {"type": "array"},
                                        "total_cohorts": {"type": "integer"},
                                        "generated_at": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        if request.endpoint not in schemas:
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error=f"Schema not found for endpoint: {request.endpoint}"
            )
        
        schema_info = schemas[request.endpoint]
        
        return APIDocsActionResponse(
            success=True,
            action=request.action,
            schema_data=schema_info,
            parameters=schema_info.get("parameters", []),
            responses=schema_info.get("responses", {})
        )
        
    except Exception as e:
        return APIDocsActionResponse(
            success=False,
            action=request.action,
            error=f"Action failed: {str(e)}"
        )

@router.post("/docs/get-examples",
    response_model=APIDocsActionResponse,
    summary="APIDocs.get_examples action",
    description="Get usage examples and cURL commands for a specific endpoint"
)
async def api_docs_get_examples(request: APIDocsActionRequest):
    """APIDocs.get_examples action - Standard contract endpoint for orchestrator calls"""
    try:
        if request.action != "get_examples":
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error="Invalid action. Expected 'get_examples'"
            )
        
        if not request.endpoint:
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error="Endpoint parameter is required for get_examples action"
            )
        
        # Define examples for different endpoints
        examples = {
            "/api/data/schema": {
                "examples": [
                    {
                        "name": "Get Database Schema",
                        "description": "Retrieve the complete database schema",
                        "response": {
                            "schema": {
                                "statements_new": [
                                    {"column": "id", "type": "integer"},
                                    {"column": "actor_id", "type": "text"}
                                ]
                            },
                            "description": "Normalized analytics data schema"
                        }
                    }
                ],
                "curl_commands": [
                    "curl -X GET 'http://localhost:8000/api/data/schema'"
                ]
            },
            "/api/data/query": {
                "examples": [
                    {
                        "name": "Get User Count",
                        "description": "Count total unique users",
                        "request": {
                            "query": "SELECT COUNT(DISTINCT actor_id) as user_count FROM statements_new"
                        },
                        "response": {
                            "query": "SELECT COUNT(DISTINCT actor_id) as user_count FROM statements_new",
                            "results": [{"user_count": 150}],
                            "count": 1,
                            "executed_at": "2024-01-20T21:45:00Z"
                        }
                    },
                    {
                        "name": "Get Recent Activity",
                        "description": "Get recent learning statements",
                        "request": {
                            "query": "SELECT actor_id, timestamp, verb FROM statements_new ORDER BY timestamp DESC LIMIT 10"
                        },
                        "response": {
                            "query": "SELECT actor_id, timestamp, verb FROM statements_new ORDER BY timestamp DESC LIMIT 10",
                            "results": [
                                {"actor_id": "user123", "timestamp": "2024-01-20T21:45:00Z", "verb": "completed"}
                            ],
                            "count": 10,
                            "executed_at": "2024-01-20T21:45:00Z"
                        }
                    }
                ],
                "curl_commands": [
                    "curl -X POST 'http://localhost:8000/api/data/query' -H 'Content-Type: application/json' -d '{\"query\": \"SELECT COUNT(DISTINCT actor_id) as user_count FROM statements_new\"}'",
                    "curl -X POST 'http://localhost:8000/api/data/query' -H 'Content-Type: application/json' -d '{\"query\": \"SELECT actor_id, timestamp, verb FROM statements_new ORDER BY timestamp DESC LIMIT 10\"}'"
                ]
            },
            "/api/analytics/cohorts": {
                "examples": [
                    {
                        "name": "Get All Cohorts",
                        "description": "Retrieve analytics for all user cohorts",
                        "response": {
                            "cohorts": [
                                {
                                    "cohort": "High Activity",
                                    "user_count": 25,
                                    "avg_interactions": 75.5
                                },
                                {
                                    "cohort": "Medium Activity", 
                                    "user_count": 45,
                                    "avg_interactions": 35.2
                                }
                            ],
                            "total_cohorts": 3,
                            "generated_at": "2024-01-20T21:45:00Z"
                        }
                    }
                ],
                "curl_commands": [
                    "curl -X GET 'http://localhost:8000/api/analytics/cohorts'"
                ]
            }
        }
        
        if request.endpoint not in examples:
            return APIDocsActionResponse(
                success=False,
                action=request.action,
                error=f"Examples not found for endpoint: {request.endpoint}"
            )
        
        example_info = examples[request.endpoint]
        
        return APIDocsActionResponse(
            success=True,
            action=request.action,
            examples=example_info.get("examples", []),
            curl_commands=example_info.get("curl_commands", [])
        )
        
    except Exception as e:
        return APIDocsActionResponse(
            success=False,
            action=request.action,
            error=f"Action failed: {str(e)}"
        )

@router.get("/docs/contract", summary="Get APIDocs app contract")
async def get_api_docs_contract():
    """Get the APIDocs app contract for orchestrator integration"""
    return {
        "name": "APIDocs",
        "description": "Browse API schema and endpoints",
        "actions": [
            {
                "name": "list_endpoints",
                "input": {},
                "output": {
                    "endpoints": "list",
                    "categories": "list"
                }
            },
            {
                "name": "get_schema",
                "input": {"endpoint": "string"},
                "output": {
                    "schema": "object",
                    "parameters": "list",
                    "responses": "object"
                }
            },
            {
                "name": "get_examples",
                "input": {"endpoint": "string"},
                "output": {
                    "examples": "list",
                    "curl_commands": "list"
                }
            }
        ],
        "endpoints": {
            "list_endpoints": "POST /api/docs/list-endpoints",
            "get_schema": "POST /api/docs/get-schema",
            "get_examples": "POST /api/docs/get-examples"
        }
    }



