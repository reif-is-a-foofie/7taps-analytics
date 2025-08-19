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

router = APIRouter(prefix="/api", tags=["Public Data API"])

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

@router.get("/health", summary="Health check")
async def health_check():
    """
    Simple health check endpoint for the public API.
    """
    return {
        "status": "healthy",
        "service": "7taps-analytics-public-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

