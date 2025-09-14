#!/usr/bin/env python3
"""
BigQuery Data Explorer

This script helps you explore and query the data in BigQuery.
"""

import os
import sys
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_bigquery_client():
    """Get BigQuery client."""
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'google-cloud-key.json')
    credentials = service_account.Credentials.from_service_account_file(key_file)
    return bigquery.Client(credentials=credentials, project="taps-data")

def show_table_info(table_name):
    """Show information about a specific table."""
    print(f"\n📊 Table: {table_name}")
    print("=" * 50)
    
    bq_client = get_bigquery_client()
    table_ref = bq_client.dataset("taps_data").table(table_name)
    table = bq_client.get_table(table_ref)
    
    print(f"Rows: {table.num_rows:,}")
    print(f"Size: {table.num_bytes / (1024*1024):.2f} MB")
    print(f"Created: {table.created}")
    print(f"Modified: {table.modified}")
    
    print("\nColumns:")
    for field in table.schema:
        print(f"  • {field.name} ({field.field_type}) - {field.mode}")
    
    return table

def show_sample_data(table_name, limit=5):
    """Show sample data from a table."""
    print(f"\n🔍 Sample Data from {table_name} (first {limit} rows):")
    print("=" * 60)
    
    bq_client = get_bigquery_client()
    query = f"SELECT * FROM `taps-data.taps_data.{table_name}` LIMIT {limit}"
    
    df = bq_client.query(query).to_dataframe()
    
    if len(df) > 0:
        print(df.to_string(index=False))
    else:
        print("No data found")
    
    return df

def run_custom_query(query):
    """Run a custom SQL query."""
    print(f"\n🔍 Custom Query:")
    print("=" * 50)
    print(query)
    print("=" * 50)
    
    bq_client = get_bigquery_client()
    df = bq_client.query(query).to_dataframe()
    
    if len(df) > 0:
        print(f"\nResults ({len(df)} rows):")
        print(df.to_string(index=False))
    else:
        print("No results found")
    
    return df

def show_data_summary():
    """Show summary of all data in the database."""
    print("🗄️  BigQuery Database Summary")
    print("=" * 60)
    
    bq_client = get_bigquery_client()
    dataset_ref = bq_client.dataset("taps_data")
    
    tables = list(bq_client.list_tables(dataset_ref))
    total_rows = 0
    
    for table in tables:
        table_obj = bq_client.get_table(table.reference)
        rows = table_obj.num_rows
        total_rows += rows
        print(f"📋 {table.table_id}: {rows:,} rows")
    
    print(f"\n📈 Total rows across all tables: {total_rows:,}")

def show_common_queries():
    """Show some common queries you can run."""
    print("\n💡 Common Queries You Can Run:")
    print("=" * 60)
    
    queries = {
        "User Statistics": """
        SELECT 
            COUNT(*) as total_users,
            COUNT(DISTINCT email) as unique_emails
        FROM `taps-data.taps_data.users`
        """,
        
        "Lesson Progress": """
        SELECT 
            l.lesson_name,
            COUNT(ua.user_id) as users_started,
            COUNT(DISTINCT ua.user_id) as unique_users
        FROM `taps-data.taps_data.lessons` l
        LEFT JOIN `taps-data.taps_data.user_activities` ua ON l.id = ua.lesson_id
        GROUP BY l.id, l.lesson_name
        ORDER BY users_started DESC
        """,
        
        "Question Response Analysis": """
        SELECT 
            q.question_text,
            COUNT(ur.id) as total_responses,
            AVG(ur.response_value) as avg_response_value
        FROM `taps-data.taps_data.questions` q
        LEFT JOIN `taps-data.taps_data.user_responses` ur ON q.id = ur.question_id
        GROUP BY q.id, q.question_text
        ORDER BY total_responses DESC
        LIMIT 10
        """,
        
        "User Activity Timeline": """
        SELECT 
            DATE(created_at) as activity_date,
            COUNT(*) as activities_count,
            COUNT(DISTINCT user_id) as active_users
        FROM `taps-data.taps_data.user_activities`
        WHERE created_at IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY activity_date DESC
        LIMIT 10
        """,
        
        "Top Active Users": """
        SELECT 
            u.email,
            COUNT(ua.id) as total_activities,
            COUNT(ur.id) as total_responses
        FROM `taps-data.taps_data.users` u
        LEFT JOIN `taps-data.taps_data.user_activities` ua ON u.id = ua.user_id
        LEFT JOIN `taps-data.taps_data.user_responses` ur ON u.id = ur.user_id
        GROUP BY u.id, u.email
        ORDER BY total_activities DESC
        LIMIT 10
        """
    }
    
    for name, query in queries.items():
        print(f"\n📊 {name}:")
        print(query.strip())

def interactive_query():
    """Interactive query mode."""
    print("\n🔍 Interactive Query Mode")
    print("=" * 50)
    print("Enter SQL queries to run against the BigQuery database.")
    print("Type 'exit' to quit, 'help' for common queries, 'tables' to see table info.")
    print()
    
    while True:
        try:
            query = input("BigQuery> ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'help':
                show_common_queries()
            elif query.lower() == 'tables':
                show_data_summary()
            elif query:
                run_custom_query(query)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main function."""
    print("🔍 BigQuery Data Explorer")
    print("=" * 60)
    
    # Show database summary
    show_data_summary()
    
    # Show info for each table
    tables = ["users", "lessons", "questions", "user_activities", "user_responses"]
    
    for table in tables:
        show_table_info(table)
        show_sample_data(table, 3)
    
    # Show common queries
    show_common_queries()
    
    # Ask if user wants interactive mode
    print("\n" + "=" * 60)
    response = input("Would you like to enter interactive query mode? (y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        interactive_query()

if __name__ == '__main__':
    main()
