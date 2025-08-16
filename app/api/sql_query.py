"""
MVP SQL Query API for direct database queries
Simple interface for querying normalized tables
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import os
import logging
import re
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Database connection pool
db_pool = None

def get_db_pool():
    """Get database connection pool"""
    global db_pool
    if db_pool is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/7taps_analytics")
        db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=database_url
        )
    return db_pool

class SQLQueryRequest(BaseModel):
    """SQL query request model"""
    sql: str
    max_rows: Optional[int] = 1000
    timeout: Optional[int] = 30

class SQLQueryResponse(BaseModel):
    """SQL query response model"""
    success: bool
    columns: List[str]
    data: List[List[Any]]
    row_count: int
    execution_time: float
    error: Optional[str] = None

def is_readonly_query(sql: str) -> bool:
    """Check if SQL query is read-only"""
    # Convert to uppercase and remove comments
    sql_upper = re.sub(r'--.*$', '', sql.upper(), flags=re.MULTILINE)
    sql_upper = re.sub(r'/\*.*?\*/', '', sql_upper, flags=re.DOTALL)
    
    # Check for dangerous keywords
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'EXECUTE', 'CALL'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    
    # Must start with SELECT
    if not sql_upper.strip().startswith('SELECT'):
        return False
    
    return True

def validate_sql_query(sql: str) -> bool:
    """Validate SQL query"""
    if not sql.strip():
        return False
    
    if not is_readonly_query(sql):
        return False
    
    return True

@router.post("/query", response_model=SQLQueryResponse)
async def execute_sql_query(request: SQLQueryRequest):
    """Execute a read-only SQL query"""
    try:
        # Validate query
        if not validate_sql_query(request.sql):
            raise HTTPException(
                status_code=400, 
                detail="Invalid query. Only read-only SELECT queries are allowed."
            )
        
        # Get database connection
        pool = get_db_pool()
        conn = pool.getconn()
        
        try:
            # Set query timeout
            conn.set_session(autocommit=False)
            cursor = conn.cursor()
            cursor.execute(f"SET statement_timeout = {request.timeout * 1000}")
            
            # Execute query
            start_time = datetime.now()
            cursor.execute(request.sql)
            
            # Fetch results with row limit
            rows = cursor.fetchmany(request.max_rows)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convert rows to list format
            data = []
            for row in rows:
                data.append(list(row))
            
            cursor.close()
            
            return SQLQueryResponse(
                success=True,
                columns=columns,
                data=data,
                row_count=len(data),
                execution_time=execution_time
            )
            
        finally:
            pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"SQL query execution failed: {e}")
        return SQLQueryResponse(
            success=False,
            columns=[],
            data=[],
            row_count=0,
            execution_time=0,
            error=str(e)
        )

@router.get("/tables")
async def get_available_tables():
    """Get list of available tables"""
    try:
        pool = get_db_pool()
        conn = pool.getconn()
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            tables = cursor.fetchall()
            cursor.close()
            
            return {
                "success": True,
                "tables": [
                    {
                        "name": table[0],
                        "type": table[1]
                    }
                    for table in tables
                ]
            }
            
        finally:
            pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        return {
            "success": False,
            "tables": [],
            "error": str(e)
        }

@router.get("/table-info/{table_name}")
async def get_table_info(table_name: str):
    """Get table schema information"""
    try:
        pool = get_db_pool()
        conn = pool.getconn()
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = cursor.fetchall()
            cursor.close()
            
            return {
                "success": True,
                "table_name": table_name,
                "columns": [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "default": col[3]
                    }
                    for col in columns
                ]
            }
            
        finally:
            pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"Failed to get table info for {table_name}: {e}")
        return {
            "success": False,
            "table_name": table_name,
            "columns": [],
            "error": str(e)
        }

@router.get("/sample-queries")
async def get_sample_queries():
    """Get sample queries for common use cases"""
    return {
        "success": True,
        "queries": [
            {
                "name": "Table Counts",
                "description": "Get counts of all tables",
                "sql": """
SELECT 'statements_flat' as table_name, COUNT(*) as count FROM statements_flat
UNION ALL
SELECT 'statements_normalized' as table_name, COUNT(*) as count FROM statements_normalized
UNION ALL
SELECT 'actors' as table_name, COUNT(*) as count FROM actors
UNION ALL
SELECT 'activities' as table_name, COUNT(*) as count FROM activities
UNION ALL
SELECT 'verbs' as table_name, COUNT(*) as count FROM verbs
                """
            },
            {
                "name": "Cohort Analysis",
                "description": "Analyze data by cohort",
                "sql": """
SELECT 
    cohort_name,
    COUNT(*) as statement_count,
    COUNT(DISTINCT actor_id) as unique_actors
FROM statements_normalized 
WHERE cohort_name IS NOT NULL 
GROUP BY cohort_name 
ORDER BY statement_count DESC
                """
            },
            {
                "name": "Top Activities",
                "description": "Most engaged activities",
                "sql": """
SELECT 
    a.activity_id,
    a.name,
    COUNT(*) as engagement_count
FROM statements_normalized sn
JOIN activities a ON sn.activity_id = a.activity_id
GROUP BY a.activity_id, a.name
ORDER BY engagement_count DESC
LIMIT 10
                """
            },
            {
                "name": "Top Actors",
                "description": "Most active learners",
                "sql": """
SELECT 
    ac.actor_id,
    ac.name,
    COUNT(*) as activity_count
FROM statements_normalized sn
JOIN actors ac ON sn.actor_id = ac.actor_id
GROUP BY ac.actor_id, ac.name
ORDER BY activity_count DESC
LIMIT 10
                """
            },
            {
                "name": "Processing Status",
                "description": "Check data processing status",
                "sql": """
SELECT 
    'statements_flat' as table_name, COUNT(*) as count FROM statements_flat
UNION ALL
SELECT 'statements_normalized' as table_name, COUNT(*) as count FROM statements_normalized
UNION ALL
SELECT 'normalization_ratio' as metric, 
       ROUND((SELECT COUNT(*) FROM statements_normalized) * 100.0 / 
             NULLIF((SELECT COUNT(*) FROM statements_flat), 0), 2) as value
                """
            }
        ]
    }
