#!/usr/bin/env python3
"""
Script to update user_responses table with lesson numbers from the new normalized data.

This script will:
1. Query the new normalized tables to get lesson numbers
2. Update the user_responses table with the correct lesson numbers
3. Ensure the dashboard shows data for lessons 6-8
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent / "app"))

def get_db_connection():
    """Get database connection."""
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    return psycopg2.connect(DATABASE_URL, sslmode=os.getenv('PGSSLMODE', 'require'))

def update_lesson_numbers():
    """Update user_responses table with lesson numbers from new normalized data."""
    try:
        print("🔧 Connecting to database...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, let's see what lesson numbers are available in the new data
        print("📊 Checking available lesson numbers in new data...")
        cursor.execute("""
            SELECT extension_value, COUNT(*) 
            FROM context_extensions_new 
            WHERE extension_key = 'https://7taps.com/lesson-number'
            GROUP BY extension_value 
            ORDER BY extension_value
        """)
        
        lesson_counts = cursor.fetchall()
        print("Available lesson numbers:")
        for lesson_num, count in lesson_counts:
            print(f"  Lesson {lesson_num}: {count} statements")
        
        # Now let's create a mapping from statement_id to lesson_number
        print("🗺️  Creating statement to lesson number mapping...")
        cursor.execute("""
            SELECT s.statement_id, ce.extension_value as lesson_number
            FROM statements_new s
            JOIN context_extensions_new ce ON s.statement_id = ce.statement_id
            WHERE ce.extension_key = 'https://7taps.com/lesson-number'
        """)
        
        statement_lesson_map = dict(cursor.fetchall())
        print(f"Created mapping for {len(statement_lesson_map)} statements")
        
        # Update user_responses table with lesson numbers
        print("📝 Updating user_responses table...")
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
        print(f"✅ Updated {updated_count} user_responses with lesson numbers")
        
        # Verify the update
        print("🔍 Verifying update...")
        cursor.execute("""
            SELECT lesson_number, COUNT(*) 
            FROM user_responses 
            WHERE lesson_number IS NOT NULL
            GROUP BY lesson_number 
            ORDER BY lesson_number
        """)
        
        updated_counts = cursor.fetchall()
        print("Updated lesson numbers in user_responses:")
        for lesson_num, count in updated_counts:
            print(f"  Lesson {lesson_num}: {count} responses")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating lesson numbers: {e}")
        return False

if __name__ == "__main__":
    update_lesson_numbers()
