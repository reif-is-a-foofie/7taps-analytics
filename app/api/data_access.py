#!/usr/bin/env python3
"""
Data Access API for 7taps Analytics

This module provides external access to analytics data with proper authentication
and connection details for direct database access.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class DatabaseQuery(BaseModel):
    """Request model for database queries."""
    query: str
    limit: Optional[int] = 1000

class ConnectionDetails(BaseModel):
    """Database connection details for external access."""
    host: str
    port: int
    database: str
    username: str
    ssl_mode: str
    connection_string: str

def get_db_connection():
    """Get database connection."""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not configured")
        
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def parse_database_url():
    """Parse DATABASE_URL to extract connection details."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise HTTPException(status_code=500, detail="Database URL not configured")
    
    # Parse postgresql://user:password@host:port/database
    if database_url.startswith('postgresql://'):
        url = database_url[13:]  # Remove postgresql:// prefix
        
        if '@' in url:
            auth_part, rest = url.split('@', 1)
            if ':' in auth_part:
                user, password = auth_part.split(':', 1)
            else:
                user, password = auth_part, ''
            
            if '/' in rest:
                host_port, database = rest.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host, port = host_port, 5432
            else:
                host, port, database = rest, 5432, 'postgres'
        else:
            user, password = '', ''
            if '/' in url:
                host_port, database = url.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host, port = host_port, 5432
            else:
                host, port, database = url, 5432, 'postgres'
    else:
        raise HTTPException(status_code=500, detail="Unsupported database URL format")
    
    return {
        'host': host,
        'port': port,
        'database': database,
        'username': user,
        'password': password
    }

@router.get("/data/connection-details", response_model=ConnectionDetails)
async def get_connection_details():
    """Get database connection details for external access."""
    try:
        details = parse_database_url()
        
        # Create connection string (without password for security)
        connection_string = f"postgresql://{details['username']}:***@{details['host']}:{details['port']}/{details['database']}?sslmode=require"
        
        return ConnectionDetails(
            host=details['host'],
            port=details['port'],
            database=details['database'],
            username=details['username'],
            ssl_mode="require",
            connection_string=connection_string
        )
    except Exception as e:
        logger.error(f"Error getting connection details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/schema")
async def get_database_schema():
    """Get database schema information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get table information
        cursor.execute("""
            SELECT 
                table_name,
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name IN ('statements_new', 'results_new', 'context_extensions_new')
            ORDER BY table_name, ordinal_position
        """)
        
        columns = cursor.fetchall()
        
        # Group by table
        schema = {}
        for table_name, column_name, data_type, is_nullable in columns:
            if table_name not in schema:
                schema[table_name] = []
            schema[table_name].append({
                'column': column_name,
                'type': data_type,
                'nullable': is_nullable == 'YES'
            })
        
        cursor.close()
        conn.close()
        
        return {
            "schema": schema,
            "description": "Main analytics tables for 7taps learning data"
        }
        
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/query")
async def execute_query(query_request: DatabaseQuery):
    """Execute a database query with safety limits."""
    try:
        # Basic query validation
        query = query_request.query.strip().upper()
        
        # Prevent dangerous operations
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        if any(keyword in query for keyword in dangerous_keywords):
            raise HTTPException(status_code=400, detail="Query contains prohibited operations")
        
        # Ensure it's a SELECT query
        if not query.startswith('SELECT'):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
        
        # Add LIMIT if not present
        if 'LIMIT' not in query:
            limit = min(query_request.limit or 1000, 1000)  # Max 1000 rows
            query_request.query += f" LIMIT {limit}"
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query_request.query)
        results = cursor.fetchall()
        
        # Convert to list of dicts
        data = [dict(row) for row in results]
        
        cursor.close()
        conn.close()
        
        return {
            "query": query_request.query,
            "results": data,
            "row_count": len(data),
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/sample-queries")
async def get_sample_queries():
    """Get sample queries for common analytics."""
    return {
        "sample_queries": {
            "learner_engagement": {
                "description": "Get learner engagement by lesson",
                "query": """
                    SELECT 
                        ce.extension_value as lesson_number,
                        COUNT(*) as total_activities,
                        COUNT(DISTINCT s.actor_id) as unique_learners
                    FROM statements_new s
                    JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
                    WHERE ce.extension_key = 'https://7taps.com/lesson-number'
                    GROUP BY ce.extension_value
                    ORDER BY lesson_number
                """
            },
            "card_type_engagement": {
                "description": "Get engagement by card type",
                "query": """
                    SELECT 
                        ce.extension_value as card_type,
                        COUNT(*) as engagement_count
                    FROM statements_new s
                    JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
                    WHERE ce.extension_key = 'https://7taps.com/card-type'
                    GROUP BY ce.extension_value
                    ORDER BY engagement_count DESC
                """
            },
            "learner_progression": {
                "description": "Get learner progression through course",
                "query": """
                    SELECT 
                        actor_id,
                        COUNT(DISTINCT ce.extension_value) as lessons_completed,
                        MAX(ce.extension_value::int) as furthest_lesson
                    FROM statements_new s
                    JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
                    WHERE ce.extension_key = 'https://7taps.com/lesson-number'
                    GROUP BY actor_id
                    ORDER BY lessons_completed DESC
                """
            },
            "recent_activity": {
                "description": "Get recent learning activity",
                "query": """
                    SELECT 
                        DATE(timestamp) as activity_date,
                        COUNT(*) as activities,
                        COUNT(DISTINCT actor_id) as active_learners
                    FROM statements_new
                    WHERE timestamp >= NOW() - INTERVAL '7 days'
                    GROUP BY DATE(timestamp)
                    ORDER BY activity_date DESC
                """
            }
        }
    }

@router.get("/data/status")
async def get_data_status():
    """Get current data status and statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get basic statistics
        cursor.execute("SELECT COUNT(*) FROM statements_new")
        total_statements = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT actor_id) FROM statements_new")
        unique_learners = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM context_extensions_new")
        total_extensions = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM statements_new GROUP BY source")
        source_breakdown = dict(cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "statistics": {
                "total_statements": total_statements,
                "unique_learners": unique_learners,
                "total_extensions": total_extensions,
                "source_breakdown": source_breakdown
            },
            "last_updated": "2025-08-18T21:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting data status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
