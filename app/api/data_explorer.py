"""
Data Explorer API for interactive data exploration.

This module provides endpoints for the data explorer tab in the dashboard,
allowing users to browse, filter, and export data from all tables.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Dict, List, Any, Optional
import psycopg2
import os
import json
from datetime import datetime
from pydantic import BaseModel

# Response models for better API documentation
class LessonResponse(BaseModel):
    id: int
    name: str
    lesson_number: Optional[int]

class UserResponse(BaseModel):
    id: int
    email: str
    user_id: str

class TableDataResponse(BaseModel):
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    total_rows: int

class ErrorResponse(BaseModel):
    success: bool
    error: str

router = APIRouter()

def get_db_connection():
    """Get database connection."""
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))

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
    """Get all lessons for the dropdown."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, lesson_name, lesson_number 
            FROM lessons 
            ORDER BY lesson_number
        """)
        
        lessons = []
        for row in cursor.fetchall():
            lessons.append({
                "id": row[0],
                "name": f"{row[2]}. {row[1]}" if row[2] else row[1],
                "lesson_number": row[2]
            })
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "lessons": lessons
        }
        
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
    """Get all users for the dropdown."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id 
            FROM users 
            ORDER BY user_id
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "email": row[1] or f"User {row[0]}",
                "user_id": row[1]
            })
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "users": users
        }
        
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
            return {
                "success": False,
                "error": f"Invalid table name. Must be one of: {', '.join(valid_tables)}"
            }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get table data with limit
        cursor.execute(f"""
            SELECT * FROM {table_name} 
            ORDER BY id 
            LIMIT %s
        """, (limit,))
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Get data
        rows = cursor.fetchall()
        data = []
        
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                # Convert datetime objects to strings
                if isinstance(value, datetime):
                    row_dict[columns[i]] = value.isoformat()
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "data": data,
            "columns": columns,
            "total_rows": len(data)
        }
        
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
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query with filters
        query = f"SELECT * FROM {table_name}"
        params = []
        conditions = []
        
        # Parse lesson_ids and user_ids from comma-separated strings
        lesson_id_list = []
        if lesson_ids:
            lesson_id_list = [int(x.strip()) for x in lesson_ids.split(',') if x.strip().isdigit()]
        
        user_id_list = []
        if user_ids:
            user_id_list = [int(x.strip()) for x in user_ids.split(',') if x.strip().isdigit()]
        
        if lesson_id_list and table_name in ['questions', 'user_activities', 'user_responses']:
            placeholders = ','.join(['%s'] * len(lesson_id_list))
            conditions.append(f"lesson_id IN ({placeholders})")
            params.extend(lesson_id_list)
        
        if user_id_list and table_name in ['user_activities', 'user_responses']:
            placeholders = ','.join(['%s'] * len(user_id_list))
            conditions.append(f"user_id IN ({placeholders})")
            params.extend(user_id_list)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY id LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Get data
        rows = cursor.fetchall()
        data = []
        
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                if isinstance(value, datetime):
                    row_dict[columns[i]] = value.isoformat()
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)
        
        cursor.close()
        conn.close()
        
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
