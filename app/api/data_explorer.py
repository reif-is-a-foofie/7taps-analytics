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
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))

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
