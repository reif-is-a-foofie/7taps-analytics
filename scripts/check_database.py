#!/usr/bin/env python3
"""
Database inspection script for 7taps analytics
Shows tables, schemas, and sample queries
"""

import os
import psycopg2
import json
from datetime import datetime

# Database connection - Heroku PostgreSQL
DATABASE_URL = "postgres://u19o5qm786p1d1:p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2@c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/d7s5ke2hmuqipn"

def get_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def get_tables():
    """Get all tables in the database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("""
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return tables

def get_table_schema(table_name):
    """Get schema for a specific table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    
    columns = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return columns

def get_sample_data(table_name, limit=5):
    """Get sample data from a table"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()
    
    # Get column names
    cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position")
    columns = [col[0] for col in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    
    return columns, rows

def generate_sample_queries():
    """Generate sample queries for common analytics tasks"""
    queries = {
        "user_analytics": {
            "description": "User engagement and completion analytics",
            "queries": [
                {
                    "name": "Total Users",
                    "sql": "SELECT COUNT(DISTINCT id) as total_users FROM users;",
                    "description": "Count total registered users"
                },
                {
                    "name": "User Activity Summary",
                    "sql": """
                        SELECT 
                            u.id,
                            u.email,
                            COUNT(ua.id) as activity_count,
                            COUNT(DISTINCT ua.lesson_id) as lessons_accessed
                        FROM users u
                        LEFT JOIN user_activities ua ON u.id = ua.user_id
                        GROUP BY u.id, u.email
                        ORDER BY activity_count DESC
                        LIMIT 10;
                    """,
                    "description": "Top 10 most active users"
                },
                {
                    "name": "Lesson Completion Rates",
                    "sql": """
                        SELECT 
                            l.lesson_name,
                            COUNT(DISTINCT ua.user_id) as users_started,
                            COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END) as users_completed,
                            ROUND(
                                (COUNT(DISTINCT CASE WHEN ua.activity_type = 'http://adlnet.gov/expapi/verbs/completed' THEN ua.user_id END)::float / 
                                 NULLIF(COUNT(DISTINCT ua.user_id), 0) * 100), 2
                            ) as completion_rate
                        FROM lessons l
                        LEFT JOIN user_activities ua ON l.id = ua.lesson_id
                        GROUP BY l.id, l.lesson_name
                        ORDER BY l.lesson_number;
                    """,
                    "description": "Completion rates by lesson"
                }
            ]
        },
        "response_analytics": {
            "description": "User response and interaction analytics",
            "queries": [
                {
                    "name": "Response Summary",
                    "sql": "SELECT COUNT(*) as total_responses FROM user_responses;",
                    "description": "Total number of user responses"
                },
                {
                    "name": "Question Response Analysis",
                    "sql": """
                        SELECT 
                            q.question_text,
                            COUNT(ur.id) as response_count,
                            AVG(ur.response_value) as avg_response
                        FROM questions q
                        LEFT JOIN user_responses ur ON q.id = ur.question_id
                        GROUP BY q.id, q.question_text
                        ORDER BY response_count DESC
                        LIMIT 10;
                    """,
                    "description": "Most answered questions with average responses"
                }
            ]
        },
        "time_analytics": {
            "description": "Time-based analytics and trends",
            "queries": [
                {
                    "name": "Activity Over Time",
                    "sql": """
                        SELECT 
                            DATE(ua.created_at) as activity_date,
                            COUNT(*) as activity_count
                        FROM user_activities ua
                        WHERE ua.created_at >= CURRENT_DATE - INTERVAL '30 days'
                        GROUP BY DATE(ua.created_at)
                        ORDER BY activity_date;
                    """,
                    "description": "Daily activity for last 30 days"
                },
                {
                    "name": "User Engagement Timeline",
                    "sql": """
                        SELECT 
                            u.email,
                            MIN(ua.created_at) as first_activity,
                            MAX(ua.created_at) as last_activity,
                            COUNT(*) as total_activities
                        FROM users u
                        JOIN user_activities ua ON u.id = ua.user_id
                        GROUP BY u.id, u.email
                        ORDER BY total_activities DESC
                        LIMIT 10;
                    """,
                    "description": "User engagement timeline"
                }
            ]
        }
    }
    return queries

def main():
    """Main function to run database inspection"""
    print("🔍 7taps Analytics Database Inspection")
    print("=" * 50)
    
    try:
        # Get tables
        print("\n📋 Database Tables:")
        print("-" * 30)
        tables = get_tables()
        
        if not tables:
            print("❌ No tables found in database")
            return
        
        for table_name, table_type in tables:
            print(f"✅ {table_name} ({table_type})")
        
        # Show table schemas
        print("\n📊 Table Schemas:")
        print("-" * 30)
        
        for table_name, table_type in tables:
            if table_type == 'BASE TABLE':
                print(f"\n🔹 {table_name}:")
                columns = get_table_schema(table_name)
                for col_name, data_type, nullable, default_val in columns:
                    nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                    print(f"  - {col_name}: {data_type} ({nullable_str})")
        
        # Show sample data
        print("\n📈 Sample Data:")
        print("-" * 30)
        
        for table_name, table_type in tables:
            if table_type == 'BASE TABLE':
                try:
                    columns, rows = get_sample_data(table_name, 3)
                    print(f"\n🔹 {table_name} (showing 3 rows):")
                    print(f"  Columns: {', '.join(columns)}")
                    for i, row in enumerate(rows, 1):
                        print(f"  Row {i}: {row}")
                except Exception as e:
                    print(f"  ❌ Error reading {table_name}: {e}")
        
        # Generate sample queries
        print("\n🔍 Sample Analytics Queries:")
        print("-" * 30)
        
        queries = generate_sample_queries()
        for category, category_data in queries.items():
            print(f"\n📊 {category_data['description']}:")
            for query in category_data['queries']:
                print(f"\n🔹 {query['name']}:")
                print(f"   Description: {query['description']}")
                print(f"   SQL: {query['sql'].strip()}")
        
        print("\n✅ Database inspection complete!")
        print(f"📅 Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
