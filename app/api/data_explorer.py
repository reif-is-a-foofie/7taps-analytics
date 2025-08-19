"""
Data Explorer API for interactive data exploration.

This module provides endpoints for the data explorer tab in the dashboard,
allowing users to browse, filter, and export data from all tables.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional
import psycopg2
import os
import json
from datetime import datetime

router = APIRouter()

def get_db_connection():
    """Get database connection."""
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(DATABASE_URL)

@router.get("/api/data-explorer/lessons")
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

@router.get("/api/data-explorer/users")
async def get_users():
    """Get all users for the dropdown."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, actor_id 
            FROM users 
            ORDER BY email, actor_id
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "email": row[1] or row[2] or f"User {row[0]}",
                "actor_id": row[2]
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

@router.get("/api/data-explorer/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 1000):
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

@router.get("/api/data-explorer/table/{table_name}/filtered")
async def get_filtered_table_data(
    table_name: str, 
    lesson_id: Optional[int] = None,
    user_id: Optional[int] = None,
    limit: int = 1000
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
        
        if lesson_id and table_name in ['questions', 'user_activities', 'user_responses']:
            conditions.append("lesson_id = %s")
            params.append(lesson_id)
        
        if user_id and table_name in ['user_activities', 'user_responses']:
            conditions.append("user_id = %s")
            params.append(user_id)
        
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
                "lesson_id": lesson_id,
                "user_id": user_id
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
