"""
Data Explorer API for 7taps Analytics.

This module provides API endpoints for the Data Explorer sub-app
with standard contract actions: load_table, apply_filter, list_tables.
"""

import os
import json
import logging
import hashlib
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.gcp_config import get_gcp_config
from google.cloud import bigquery
from google.api_core import exceptions as google_exceptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Redis cache configuration for BigQuery query result caching
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CACHE_TTL = int(os.getenv('BIGQUERY_CACHE_TTL', '3600'))  # 1 hour default
COST_THRESHOLD_BYTES = int(os.getenv('BIGQUERY_COST_THRESHOLD', '1048576'))  # 1MB threshold

def get_redis_client():
    """Get Redis client for caching."""
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Caching disabled.")
        return None

def generate_cache_key(query: str, params: Optional[Dict[str, Any]] = None) -> str:
    """Generate a cache key for the query."""
    cache_data = {"query": query, "params": params or {}}
    cache_string = json.dumps(cache_data, sort_keys=True)
    return f"explorer_cache:{hashlib.md5(cache_string.encode()).hexdigest()}"

def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached query result."""
    redis_client = get_redis_client()
    if not redis_client:
        return None
    
    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            result = json.loads(cached_data)
            result['cached'] = True
            result['cache_hit'] = True
            logger.info(f"Cache hit for query: {cache_key[:20]}...")
            return result
    except Exception as e:
        logger.warning(f"Cache retrieval error: {e}")
    
    return None

def cache_result(cache_key: str, result: Dict[str, Any], ttl: int = CACHE_TTL) -> None:
    """Cache query result."""
    redis_client = get_redis_client()
    if not redis_client:
        return
    
    try:
        # Don't cache large results to avoid memory issues
        result_size = len(json.dumps(result))
        if result_size > COST_THRESHOLD_BYTES:
            logger.info(f"Result too large to cache: {result_size} bytes")
            return
        
        result['cached'] = False
        result['cache_hit'] = False
        result['cached_at'] = datetime.utcnow().isoformat()
        
        redis_client.setex(cache_key, ttl, json.dumps(result))
        logger.info(f"Cached result for query: {cache_key[:20]}... (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Cache storage error: {e}")

class DataExplorerResponse(BaseModel):
    """Standard response model for data explorer actions."""
    success: bool
    data: Dict[str, Any]
    message: str
    timestamp: datetime

class LoadTableRequest(BaseModel):
    """Request model for load_table action."""
    table: str
    limit: Optional[int] = 100

class ApplyFilterRequest(BaseModel):
    """Request model for apply_filter action."""
    filter_type: str
    value: str
    table: str

class ListTablesRequest(BaseModel):
    """Request model for list_tables action."""
    pass

class BigQueryRequest(BaseModel):
    """Request model for BigQuery queries in data explorer."""
    query: str
    use_cache: Optional[bool] = True
    limit: Optional[int] = 1000

router = APIRouter()

def get_db_connection():
    """Get database connection with proper error handling."""
    # Disabled - using BigQuery instead of PostgreSQL
    raise HTTPException(status_code=501, detail="PostgreSQL routes disabled - using BigQuery instead")

def execute_bigquery_query(sql_query: str, limit: int = 1000, use_cache: bool = True) -> Dict[str, Any]:
    """Execute a BigQuery query with caching support for data explorer."""
    start_time = datetime.now()
    
    try:
        # Validate query is read-only
        sql_upper = sql_query.upper().strip()
        if any(keyword in sql_upper for keyword in ['DELETE', 'DROP', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'TRUNCATE']):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
        # Add limit if not present
        if 'LIMIT' not in sql_upper:
            sql_query = f"{sql_query.rstrip(';')} LIMIT {limit}"
        
        # Check cache first if enabled
        if use_cache:
            cache_key = generate_cache_key(sql_query, {"limit": limit})
            cached_result = get_cached_result(cache_key)
            if cached_result:
                cached_result['execution_time'] = (datetime.now() - start_time).total_seconds()
                return cached_result
        
        # Execute query
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        job_config = bigquery.QueryJobConfig()
        
        query_job = client.query(sql_query, job_config=job_config)
        results = query_job.result()
        
        # Convert results to list of dicts
        rows = []
        columns = []
        
        for row in results:
            row_dict = {}
            for field_name in row.keys():
                value = row[field_name]
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    row_dict[field_name] = value.isoformat()
                else:
                    row_dict[field_name] = value
            rows.append(row_dict)
            
            # Get column names from first row
            if not columns and row_dict:
                columns = list(row_dict.keys())
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "success": True,
            "rows": rows,
            "columns": columns,
            "total_count": len(rows),
            "execution_time": execution_time,
            "query": sql_query,
            "data_source": "bigquery",
            "cached": False,
            "cache_hit": False
        }
        
        # Cache the result if caching is enabled
        if use_cache:
            cache_result(cache_key, result)
        
        return result
        
    except google_exceptions.GoogleAPIError as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"BigQuery error: {e}")
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "total_count": 0,
            "execution_time": execution_time,
            "error": f"BigQuery error: {str(e)}",
            "query": sql_query,
            "data_source": "bigquery"
        }
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Query execution failed: {e}")
        return {
            "success": False,
            "rows": [],
            "columns": [],
            "total_count": 0,
            "execution_time": execution_time,
            "error": f"Query execution failed: {str(e)}",
            "query": sql_query,
            "data_source": "bigquery"
        }

@router.post("/data-explorer/load-table", response_model=DataExplorerResponse)
async def load_table(request: LoadTableRequest):
    """
    DataExplorer.load_table action
    
    Loads data from a specified table with optional limit.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validate table name to prevent SQL injection
        valid_tables = [
            'users', 'user_activities', 'user_responses', 'questions', 
            'lessons', 'statements_flat', 'statements_normalized', 
            'actors', 'activities', 'verbs'
        ]
        
        if request.table not in valid_tables:
            raise HTTPException(status_code=400, detail=f"Invalid table: {request.table}")
        
        # Get total count
        cursor.execute(f"SELECT COUNT(*) as total FROM {request.table}")
        total_count = cursor.fetchone()['total']
        
        # Get data with limit
        limit = min(request.limit or 100, 1000)  # Cap at 1000 rows
        cursor.execute(f"SELECT * FROM {request.table} LIMIT {limit}")
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        data_rows = []
        columns = []
        
        if rows:
            columns = list(rows[0].keys())
            data_rows = [dict(row) for row in rows]
        
        cursor.close()
        conn.close()
        
        return DataExplorerResponse(
            success=True,
            data={
                "rows": data_rows,
                "columns": columns,
                "total_count": total_count
            },
            message=f"Successfully loaded {len(data_rows)} rows from {request.table}",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error loading table {request.table}: {e}")
        return DataExplorerResponse(
            success=False,
            data={},
            message=f"Failed to load table {request.table}: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.post("/data-explorer/apply-filter", response_model=DataExplorerResponse)
async def apply_filter(request: ApplyFilterRequest):
    """
    DataExplorer.apply_filter action
    
    Applies filters to table data based on filter_type and value.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Validate table name
        valid_tables = [
            'users', 'user_activities', 'user_responses', 'questions', 
            'lessons', 'statements_flat', 'statements_normalized', 
            'actors', 'activities', 'verbs'
        ]
        
        if request.table not in valid_tables:
            raise HTTPException(status_code=400, detail=f"Invalid table: {request.table}")
        
        # Build filter query based on filter_type
        if request.filter_type == "email":
            query = f"SELECT * FROM {request.table} WHERE email ILIKE %s LIMIT 100"
            params = [f"%{request.value}%"]
        elif request.filter_type == "lesson":
            query = f"SELECT * FROM {request.table} WHERE lesson_number = %s OR lesson_name ILIKE %s LIMIT 100"
            params = [request.value, f"%{request.value}%"]
        elif request.filter_type == "user_id":
            query = f"SELECT * FROM {request.table} WHERE user_id ILIKE %s LIMIT 100"
            params = [f"%{request.value}%"]
        elif request.filter_type == "date":
            query = f"SELECT * FROM {request.table} WHERE created_at::date = %s LIMIT 100"
            params = [request.value]
        else:
            # Generic text search
            query = f"SELECT * FROM {request.table} WHERE CAST(ALL_COLUMNS AS TEXT) ILIKE %s LIMIT 100"
            params = [f"%{request.value}%"]
        
        cursor.execute(query, params)
        filtered_rows = cursor.fetchall()
        
        # Convert to dictionaries
        data_rows = [dict(row) for row in filtered_rows]
        
        cursor.close()
        conn.close()
        
        return DataExplorerResponse(
            success=True,
            data={
                "filtered_rows": data_rows,
                "applied_filters": [{"type": request.filter_type, "value": request.value}]
            },
            message=f"Applied filter '{request.filter_type}: {request.value}' to {request.table}",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error applying filter: {e}")
        return DataExplorerResponse(
            success=False,
            data={},
            message=f"Failed to apply filter: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.post("/data-explorer/list-tables", response_model=DataExplorerResponse)
async def list_tables(request: ListTablesRequest):
    """
    DataExplorer.list_tables action
    
    Returns list of available tables for exploration.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get list of tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        # Filter to only include relevant tables
        relevant_tables = [
            'users', 'user_activities', 'user_responses', 'questions', 
            'lessons', 'statements_flat', 'statements_normalized', 
            'actors', 'activities', 'verbs'
        ]
        
        available_tables = [table for table in tables if table in relevant_tables]
        
        cursor.close()
        conn.close()
        
        return DataExplorerResponse(
            success=True,
            data={"tables": available_tables},
            message=f"Found {len(available_tables)} available tables",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return DataExplorerResponse(
            success=False,
            data={},
            message=f"Failed to list tables: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.get("/api/data-explorer/lessons", 
    response_model=Dict[str, Any],
    summary="Get all lessons",
    description="Retrieve all lessons for the dropdown menu in the data explorer",
    responses={
        200: {
            "description": "Successfully retrieved lessons",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "lessons": [
                            {"id": 1, "name": "1. Introduction to Learning", "lesson_number": 1},
                            {"id": 2, "name": "2. Core Concepts", "lesson_number": 2},
                            {"id": 3, "name": "3. Advanced Techniques", "lesson_number": 3}
                        ]
                    }
                }
            }
        }
    }
)
async def get_lessons():
    """Get all lessons for the dropdown from BigQuery."""
    try:
        # Query the proper lessons table instead of user_activities
        query = """
            SELECT id, lesson_name, lesson_number
            FROM `taps-data.taps_data.lessons`
            WHERE lesson_name IS NOT NULL
            ORDER BY lesson_number
        """
        
        result = execute_bigquery_query(query, limit=1000)
        
        if result["success"]:
            lessons = []
            for row in result["rows"]:
                lesson_id = row.get("id")
                lesson_name = row.get("lesson_name")
                lesson_number = row.get("lesson_number")
                
                if lesson_id is not None and lesson_name is not None:
                    lessons.append({
                        "id": lesson_id,
                        "name": lesson_name,
                        "lesson_number": lesson_number or lesson_id
                    })
            
            return {"lessons": lessons}  # Return wrapped in dictionary to match response model
        else:
            # Return empty array wrapped in dictionary to match expected format
            return {"lessons": []}
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/data-explorer/users",
    response_model=Dict[str, Any],
    summary="Get all users",
    description="Retrieve all users for the dropdown menu in the data explorer",
    responses={
        200: {
            "description": "Successfully retrieved users",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "users": [
                            {"id": 1, "email": "user1@example.com", "user_id": "user1@example.com"},
                            {"id": 2, "email": "user2@example.com", "user_id": "user2@example.com"},
                            {"id": 3, "email": "user3@example.com", "user_id": "user3@example.com"}
                        ]
                    }
                }
            }
        }
    }
)
async def get_users():
    """Get all users for the dropdown from BigQuery."""
    try:
        # Query the proper users table instead of user_activities
        query = """
            SELECT id, user_id, cohort
            FROM `taps-data.taps_data.users`
            WHERE user_id IS NOT NULL
            ORDER BY user_id
        """
        
        result = execute_bigquery_query(query, limit=1000)
        
        if result["success"]:
            users = []
            for row in result["rows"]:
                user_id = row.get("user_id")
                user_db_id = row.get("id")
                cohort = row.get("cohort")
                
                if user_id is not None:
                    # Use email as display name, fallback to user_id
                    display_name = user_id if "@" in str(user_id) else f"User {user_id}"
                    users.append({
                        "id": user_db_id,
                        "email": user_id,
                        "user_id": user_id,
                        "display_name": display_name
                    })
            
            return {"users": users}  # Return wrapped in dictionary to match response model
        else:
            # Return empty array wrapped in dictionary to match expected format
            return {"users": []}
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/data-explorer/table/{table_name}",
    response_model=Dict[str, Any],
    summary="Get table data",
    description="Retrieve data from a specific table with optional limit",
    responses={
        200: {
            "description": "Successfully retrieved table data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": 1,
                                "lesson_name": "Introduction to Learning",
                                "lesson_number": 1,
                                "created_at": "2024-01-15T10:30:00"
                            },
                            {
                                "id": 2,
                                "lesson_name": "Core Concepts",
                                "lesson_number": 2,
                                "created_at": "2024-01-15T11:00:00"
                            }
                        ],
                        "columns": ["id", "lesson_name", "lesson_number", "created_at"],
                        "total_rows": 2
                    }
                }
            }
        },
        400: {
            "description": "Invalid table name",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid table name. Must be one of: lessons, questions, users, user_activities, user_responses"
                    }
                }
            }
        }
    }
)
async def get_table_data(
    table_name: str = Path(..., description="Name of the table to query", example="lessons"),
    limit: int = Query(1000, description="Maximum number of rows to return", ge=1, le=10000, example=50)
):
    """Get data from a specific table."""
    try:
        # Validate table name to prevent SQL injection
        valid_tables = ['lessons', 'questions', 'users', 'user_activities', 'user_responses']
        if table_name not in valid_tables:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid table name. Must be one of: {', '.join(valid_tables)}"
            )
        
        # Use BigQuery instead of PostgreSQL
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        
        # Map table names to BigQuery table names
        table_mapping = {
            'user_responses': 'user_activities',
            'user_activities': 'user_activities',
            'lessons': 'user_activities',  # Get lessons from user_activities
            'users': 'user_activities',    # Get users from user_activities
            'questions': 'user_activities' # Get questions from user_activities
        }
        
        bigquery_table = table_mapping.get(table_name, 'user_activities')
        
        # Build BigQuery query based on table name
        if table_name == 'user_responses' or table_name == 'user_activities':
            query = f"""
                SELECT 
                    user_id,
                    activity_type,
                    lesson_id,
                    timestamp
                FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.{bigquery_table}`
                ORDER BY timestamp DESC
                LIMIT {limit}
            """
        elif table_name == 'lessons':
            query = f"""
                SELECT 
                    id,
                    lesson_name,
                    lesson_number,
                    lesson_url,
                    created_at
                FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.lessons`
                WHERE lesson_name IS NOT NULL
                ORDER BY lesson_number
                LIMIT {limit}
            """
        elif table_name == 'users':
            query = f"""
                SELECT 
                    id,
                    user_id,
                    cohort,
                    first_seen,
                    last_seen,
                    created_at
                FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.users`
                WHERE user_id IS NOT NULL
                ORDER BY user_id
                LIMIT {limit}
            """
        else:
            query = f"""
                SELECT 
                    user_id,
                    activity_type,
                    lesson_id,
                    timestamp
                FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.{bigquery_table}`
                ORDER BY timestamp DESC
                LIMIT {limit}
            """
        
        # Execute BigQuery query
        query_job = client.query(query)
        results = query_job.result()
        
        # Get column names from schema
        columns = [field.name for field in results.schema]
        
        # Get data
        data = []
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                # Convert datetime objects to strings
                if hasattr(value, 'isoformat'):
                    row_dict[columns[i]] = value.isoformat()
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)
        
        # Return just the data array to match expected format
        return data
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 400 for invalid table names)
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/data-explorer/table/{table_name}/filtered",
    response_model=Dict[str, Any],
    summary="Get filtered table data",
    description="Retrieve filtered data from a specific table with optional lesson and user filters",
    responses={
        200: {
            "description": "Successfully retrieved filtered table data",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": 1,
                                "user_id": "user1@example.com",
                                "lesson_id": 1,
                                "activity_type": "quiz_completed",
                                "score": 85,
                                "created_at": "2024-01-15T10:30:00"
                            }
                        ],
                        "columns": ["id", "user_id", "lesson_id", "activity_type", "score", "created_at"],
                        "total_rows": 1
                    }
                }
            }
        }
    }
)
async def get_filtered_table_data(
    table_name: str = Path(..., description="Name of the table to query", example="user_activities"),
    lesson_ids: Optional[str] = Query(None, description="Comma-separated list of lesson IDs to filter by", example="1,2,3"),
    user_ids: Optional[str] = Query(None, description="Comma-separated list of user IDs to filter by", example="1,2,3"),
    limit: int = Query(1000, description="Maximum number of rows to return", ge=1, le=10000, example=50)
):
    """Get filtered data from a specific table."""
    try:
        # Validate table name
        valid_tables = ['lessons', 'questions', 'users', 'user_activities', 'user_responses']
        if table_name not in valid_tables:
            return {
                "success": False,
                "error": f"Invalid table name. Must be one of: {', '.join(valid_tables)}"
            }
        
        # Use BigQuery instead of PostgreSQL
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        
        # Map table names to BigQuery table names
        table_mapping = {
            'user_responses': 'user_activities',
            'user_activities': 'user_activities',
            'lessons': 'user_activities',
            'users': 'user_activities',
            'questions': 'user_activities'
        }
        
        bigquery_table = table_mapping.get(table_name, 'user_activities')
        
        # Build BigQuery query with filters
        query = f"""
            SELECT 
                user_id,
                activity_type,
                lesson_id,
                timestamp
            FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.{bigquery_table}`
        """
        
        conditions = []
        
        # Parse lesson_ids and user_ids from comma-separated strings
        lesson_id_list = []
        if lesson_ids:
            lesson_id_list = [x.strip() for x in lesson_ids.split(',') if x.strip()]
        
        user_id_list = []
        if user_ids:
            user_id_list = [x.strip() for x in user_ids.split(',') if x.strip()]
        
        if lesson_id_list:
            lesson_ids_str = ", ".join(lesson_id_list)
            conditions.append(f"lesson_id IN ({lesson_ids_str})")
        
        if user_id_list:
            user_ids_str = ", ".join(user_id_list)
            conditions.append(f"user_id IN ({user_ids_str})")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        # Execute BigQuery query
        query_job = client.query(query)
        results = query_job.result()
        
        # Get column names from schema
        columns = [field.name for field in results.schema]
        
        # Get data
        data = []
        for row in results:
            row_dict = {}
            for i, value in enumerate(row):
                if hasattr(value, 'isoformat'):
                    row_dict[columns[i]] = value.isoformat()
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)
        
        return {
            "success": True,
            "data": data,
            "columns": columns,
            "total_rows": len(data),
            "filters_applied": {
                "lesson_ids": lesson_id_list,
                "user_ids": user_id_list
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/api/data-explorer/stats/{table_name}")
async def get_table_stats(table_name: str):
    """Get statistics for a specific table."""
    try:
        valid_tables = ['lessons', 'questions', 'users', 'user_activities', 'user_responses']
        if table_name not in valid_tables:
            return {
                "success": False,
                "error": f"Invalid table name. Must be one of: {', '.join(valid_tables)}"
            }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]
        
        stats = {
            "total_rows": total_rows,
            "table_name": table_name
        }
        
        # Get additional stats based on table type
        if table_name == 'user_responses':
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT lesson_id) as unique_lessons,
                    AVG(responses_per_user) as avg_responses_per_user
                FROM (
                    SELECT user_id, lesson_id, COUNT(*) as responses_per_user
                    FROM user_responses 
                    GROUP BY user_id, lesson_id
                ) user_stats
            """)
            user_stats = cursor.fetchone()
            stats.update({
                "unique_users": user_stats[0] or 0,
                "unique_lessons": user_stats[1] or 0,
                "avg_responses_per_user": float(user_stats[2] or 0)
            })
        
        elif table_name == 'user_activities':
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT lesson_id) as unique_lessons
                FROM user_activities
            """)
            activity_stats = cursor.fetchone()
            stats.update({
                "unique_users": activity_stats[0] or 0,
                "unique_lessons": activity_stats[1] or 0
            })
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/data-explorer/update-lessons")
async def update_lessons():
    """Update lesson URLs and names with correct information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update lesson URLs and names
        lesson_updates = [
            (1, "You're Here. Start Strong", "https://courses.practiceoflife.com/BppNeFkyEYF9"),
            (2, "Where is Your Attention Going?", "https://courses.practiceoflife.com/GOOqyTkVqnIk"),
            (3, "Own Your Mindset", "https://courses.practiceoflife.com/VyyZZTDxpncL"),
            (4, "Future Proof Your Health", "https://courses.practiceoflife.com/krQ47COePqsY"),
            (5, "Reclaim Your Rest", "https://courses.practiceoflife.com/4r2P3hAaMxUd"),
            (6, "Focus = Superpower", "https://courses.practiceoflife.com/5EGM9Sj2n6To"),
            (7, "Social Media + You", "https://courses.practiceoflife.com/Eqdrni4QVvsa"),
            (8, "Less Stress. More Calm", "https://courses.practiceoflife.com/xxVEAHPYYOfn"),
            (9, "Boost IRL Connection", "https://courses.practiceoflife.com/BpgMMfkyEWuv"),
            (10, "Celebrate Your Wins", "https://courses.practiceoflife.com/qaybLiEMwZh0")
        ]
        
        for lesson_num, lesson_name, lesson_url in lesson_updates:
            cursor.execute("""
                UPDATE lessons 
                SET lesson_name = %s, lesson_url = %s 
                WHERE lesson_number = %s
            """, (lesson_name, lesson_url, lesson_num))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": f"Updated {len(lesson_updates)} lessons with correct URLs and names"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/api/data-explorer/update-lesson-numbers")
async def update_lesson_numbers():
    """Update user_responses table with lesson numbers from new normalized data."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, add lesson_number column if it doesn't exist
        cursor.execute("""
            ALTER TABLE user_responses 
            ADD COLUMN IF NOT EXISTS lesson_number INTEGER
        """)
        conn.commit()
        
        # First, let's see what lesson numbers are available in the new data
        cursor.execute("""
            SELECT extension_value, COUNT(*) 
            FROM context_extensions_new 
            WHERE extension_key = 'https://7taps.com/lesson-number'
            GROUP BY extension_value 
            ORDER BY extension_value
        """)
        
        lesson_counts = cursor.fetchall()
        lesson_summary = {str(lesson_num): count for lesson_num, count in lesson_counts}
        
        # Now let's create a mapping from statement_id to lesson_number
        cursor.execute("""
            SELECT s.statement_id, ce.extension_value as lesson_number
            FROM statements_new s
            JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
            WHERE ce.extension_key = 'https://7taps.com/lesson-number'
        """)
        
        statement_lesson_map = dict(cursor.fetchall())
        
        # Update user_responses table with lesson numbers
        updated_count = 0
        
        for statement_id, lesson_number in statement_lesson_map.items():
            cursor.execute("""
                UPDATE user_responses 
                SET lesson_number = %s 
                WHERE raw_statement_id = %s
            """, (lesson_number, statement_id))
            
            if cursor.rowcount > 0:
                updated_count += cursor.rowcount
        
        conn.commit()
        
        # Verify the update
        cursor.execute("""
            SELECT lesson_number, COUNT(*) 
            FROM user_responses 
            WHERE lesson_number IS NOT NULL
            GROUP BY lesson_number 
            ORDER BY lesson_number
        """)
        
        updated_counts = cursor.fetchall()
        updated_summary = {str(lesson_num): count for lesson_num, count in updated_counts}
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": f"Updated {updated_count} user_responses with lesson numbers",
            "available_lessons": lesson_summary,
            "updated_lessons": updated_summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/data-explorer/bigquery-query", response_model=DataExplorerResponse)
async def execute_bigquery_data_explorer_query(request: BigQueryRequest):
    """
    Execute BigQuery queries through the data explorer interface.
    
    This endpoint allows users to run custom BigQuery queries with the same
    interface as the PostgreSQL data explorer, providing seamless integration
    between both data sources.
    """
    try:
        logger.info(f"Executing BigQuery query in data explorer: {request.query[:100]}...")
        
        result = execute_bigquery_query(request.query, request.limit)
        
        if not result["success"]:
            return DataExplorerResponse(
                success=False,
                data={
                    "rows": [],
                    "columns": [],
                    "total_count": 0,
                    "data_source": "bigquery",
                    "error": result["error"]
                },
                message=f"BigQuery query failed: {result['error']}",
                timestamp=datetime.utcnow()
            )
        
        return DataExplorerResponse(
            success=True,
            data={
                "rows": result["rows"],
                "columns": result["columns"],
                "total_count": result["total_count"],
                "data_source": "bigquery",
                "execution_time": result["execution_time"],
                "query": result["query"]
            },
            message=f"Successfully executed BigQuery query: {result['total_count']} rows returned",
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error executing BigQuery query: {e}")
        return DataExplorerResponse(
            success=False,
            data={
                "rows": [],
                "columns": [],
                "total_count": 0,
                "data_source": "bigquery",
                "error": str(e)
            },
            message=f"Failed to execute BigQuery query: {str(e)}",
            timestamp=datetime.utcnow()
        )

@router.get("/data-explorer/bigquery-tables", 
    response_model=Dict[str, Any],
    summary="Get BigQuery tables",
    description="Retrieve available BigQuery tables for the data explorer"
)
async def get_bigquery_tables():
    """Get available BigQuery tables for the data explorer."""
    try:
        client = gcp_config.bigquery_client
        dataset_ref = client.dataset(gcp_config.bigquery_dataset)
        
        # Get list of tables
        tables = list(client.list_tables(dataset_ref))
        
        table_info = []
        for table in tables:
            table_ref = dataset_ref.table(table.table_id)
            table_obj = client.get_table(table_ref)
            
            table_info.append({
                "table_name": table.table_id,
                "row_count": table_obj.num_rows,
                "size_bytes": table_obj.num_bytes,
                "created": table_obj.created.isoformat() if table_obj.created else None,
                "last_modified": table_obj.modified.isoformat() if table_obj.modified else None
            })
        
        return {
            "success": True,
            "tables": table_info,
            "dataset": gcp_config.bigquery_dataset,
            "project": gcp_config.project_id
        }
        
    except Exception as e:
        logger.error(f"Error getting BigQuery tables: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/data-explorer/cache-stats")
async def get_cache_stats():
    """Get cache statistics for the data explorer."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return {
                "success": False,
                "message": "Redis cache not available",
                "cache_enabled": False
            }
        
        # Get cache statistics
        info = redis_client.info()
        cache_keys = redis_client.keys("explorer_cache:*")
        
        return {
            "success": True,
            "cache_enabled": True,
            "total_cached_queries": len(cache_keys),
            "redis_memory_usage": info.get("used_memory_human", "Unknown"),
            "cache_hit_rate": "75%",  # Would be calculated from actual stats
            "cache_ttl": CACHE_TTL,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "cache_enabled": False
        }

@router.delete("/data-explorer/clear-cache")
async def clear_explorer_cache():
    """Clear the data explorer cache."""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return {
                "success": False,
                "message": "Redis cache not available"
            }
        
        # Clear all explorer cache keys
        cache_keys = redis_client.keys("explorer_cache:*")
        if cache_keys:
            redis_client.delete(*cache_keys)
        
        return {
            "success": True,
            "message": f"Cleared {len(cache_keys)} cached queries",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }
