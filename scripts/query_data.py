#!/usr/bin/env python3
"""
Working BigQuery data query tool
"""

import os
import sys
from google.cloud import bigquery
from google.oauth2 import service_account

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_bigquery_client():
    """Get BigQuery client."""
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'google-cloud-key.json')
    credentials = service_account.Credentials.from_service_account_file(key_file)
    return bigquery.Client(credentials=credentials, project="taps-data")

def run_query(query):
    """Run a BigQuery and return results."""
    bq_client = get_bigquery_client()
    query_job = bq_client.query(query)
    results = query_job.result()
    return results

def show_table_data(table_name, limit=5):
    """Show data from a specific table."""
    print(f"\n📊 Sample data from {table_name} table:")
    print("=" * 60)
    
    query = f"""
    SELECT * 
    FROM `taps-data.taps_data.{table_name}` 
    LIMIT {limit}
    """
    
    try:
        results = run_query(query)
        
        # Convert to list to avoid iterator issues
        rows = list(results)
        
        if rows:
            # Print column headers
            columns = list(rows[0].keys())
            header = " | ".join(columns)
            print(header)
            print("-" * len(header))
            
            # Print data rows
            for row in rows:
                values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                print(" | ".join(values))
        else:
            print("No data found")
            
    except Exception as e:
        print(f"Error querying {table_name}: {e}")

def show_table_schema(table_name):
    """Show table schema."""
    print(f"\n📋 Schema for {table_name} table:")
    print("=" * 50)
    
    bq_client = get_bigquery_client()
    table_ref = bq_client.dataset("taps_data").table(table_name)
    table = bq_client.get_table(table_ref)
    
    print(f"Rows: {table.num_rows:,}")
    print(f"Size: {table.num_bytes / (1024*1024):.2f} MB")
    print("\nColumns:")
    for field in table.schema:
        print(f"  • {field.name} ({field.field_type}) - {field.mode}")

def main():
    """Main function."""
    print("🗄️  BigQuery Data Explorer")
    print("=" * 60)
    
    # Show schema and sample data for each table
    tables = ["users", "lessons", "questions", "user_activities", "user_responses"]
    
    for table in tables:
        show_table_schema(table)
        show_table_data(table, 3)
    
    # Show some interesting queries
    print("\n💡 Interesting Queries:")
    print("=" * 60)
    
    # User count by cohort
    print("\n1. Users by cohort:")
    try:
        query = """
        SELECT cohort, COUNT(*) as user_count
        FROM `taps-data.taps_data.users`
        WHERE cohort IS NOT NULL
        GROUP BY cohort
        ORDER BY user_count DESC
        """
        results = run_query(query)
        rows = list(results)
        if rows:
            for row in rows:
                print(f"  {row.cohort}: {row.user_count} users")
        else:
            print("  No cohort data found")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Lesson activity
    print("\n2. Most active lessons:")
    try:
        query = """
        SELECT l.lesson_name, COUNT(ua.id) as activity_count
        FROM `taps-data.taps_data.lessons` l
        LEFT JOIN `taps-data.taps_data.user_activities` ua ON l.id = ua.lesson_id
        GROUP BY l.id, l.lesson_name
        ORDER BY activity_count DESC
        LIMIT 5
        """
        results = run_query(query)
        rows = list(results)
        if rows:
            for row in rows:
                print(f"  {row.lesson_name}: {row.activity_count} activities")
        else:
            print("  No activity data found")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Response analysis
    print("\n3. Question response analysis:")
    try:
        query = """
        SELECT 
            q.question_text,
            COUNT(ur.id) as response_count,
            AVG(ur.response_value) as avg_score
        FROM `taps-data.taps_data.questions` q
        LEFT JOIN `taps-data.taps_data.user_responses` ur ON q.id = ur.question_id
        GROUP BY q.id, q.question_text
        HAVING response_count > 0
        ORDER BY response_count DESC
        LIMIT 3
        """
        results = run_query(query)
        rows = list(results)
        if rows:
            for row in rows:
                print(f"  Q: {row.question_text[:50]}...")
                print(f"     Responses: {row.response_count}, Avg Score: {row.avg_score:.2f}")
        else:
            print("  No response data found")
    except Exception as e:
        print(f"  Error: {e}")
    
    print("\n🔍 How to Query Your Data:")
    print("=" * 60)
    print("Use these patterns in Google Cloud Console BigQuery:")
    print()
    print("• View all users: SELECT * FROM `taps-data.taps_data.users`")
    print("• Count activities: SELECT COUNT(*) FROM `taps-data.taps_data.user_activities`")
    print("• User progress: SELECT u.user_id, COUNT(ua.id) as activities FROM `taps-data.taps_data.users` u LEFT JOIN `taps-data.taps_data.user_activities` ua ON u.id = ua.user_id GROUP BY u.id, u.user_id")
    print("• Response rates: SELECT question_id, COUNT(*) as responses, AVG(response_value) as avg_score FROM `taps-data.taps_data.user_responses` GROUP BY question_id")

if __name__ == '__main__':
    main()
