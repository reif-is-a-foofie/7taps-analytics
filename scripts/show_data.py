#!/usr/bin/env python3
"""
Simple script to show data from BigQuery
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

def show_table_data(table_name, limit=5):
    """Show data from a specific table."""
    print(f"\n📊 Data from {table_name} table:")
    print("=" * 60)
    
    bq_client = get_bigquery_client()
    query = f"""
    SELECT * 
    FROM `taps-data.taps_data.{table_name}` 
    LIMIT {limit}
    """
    
    try:
        query_job = bq_client.query(query)
        results = query_job.result()
        
        # Print column headers
        if results.total_rows > 0:
            first_row = next(iter(results))
            columns = list(first_row.keys())
            print(" | ".join(columns))
            print("-" * (len(" | ".join(columns))))
            
            # Print data rows
            for row in results:
                values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                print(" | ".join(values))
        else:
            print("No data found")
            
    except Exception as e:
        print(f"Error querying {table_name}: {e}")

def show_table_count(table_name):
    """Show row count for a table."""
    bq_client = get_bigquery_client()
    query = f"SELECT COUNT(*) as count FROM `taps-data.taps_data.{table_name}`"
    
    try:
        query_job = bq_client.query(query)
        results = query_job.result()
        count = next(iter(results))['count']
        return count
    except Exception as e:
        print(f"Error counting {table_name}: {e}")
        return 0

def main():
    """Main function."""
    print("🗄️  BigQuery Data Overview")
    print("=" * 60)
    
    # Show counts for all tables
    tables = ["users", "lessons", "questions", "user_activities", "user_responses", "xapi_events"]
    
    print("Table Row Counts:")
    for table in tables:
        count = show_table_count(table)
        print(f"  📋 {table}: {count:,} rows")
    
    # Show sample data from each table
    for table in tables:
        show_table_data(table, 3)
    
    print("\n💡 How to Query Your Data:")
    print("=" * 60)
    print("You can query your data using these patterns:")
    print()
    print("1. Basic SELECT:")
    print("   SELECT * FROM `taps-data.taps_data.users` LIMIT 10")
    print()
    print("2. Count records:")
    print("   SELECT COUNT(*) FROM `taps-data.taps_data.user_activities`")
    print()
    print("3. Join tables:")
    print("   SELECT u.user_id, l.lesson_name")
    print("   FROM `taps-data.taps_data.users` u")
    print("   JOIN `taps-data.taps_data.user_activities` ua ON u.id = ua.user_id")
    print("   JOIN `taps-data.taps_data.lessons` l ON ua.lesson_id = l.id")
    print()
    print("4. Filter data:")
    print("   SELECT * FROM `taps-data.taps_data.user_responses`")
    print("   WHERE response_value > 0.8")
    print()
    print("5. Group and aggregate:")
    print("   SELECT lesson_id, COUNT(*) as activity_count")
    print("   FROM `taps-data.taps_data.user_activities`")
    print("   GROUP BY lesson_id")
    print("   ORDER BY activity_count DESC")
    print()
    print("🔍 You can run these queries in:")
    print("  • Google Cloud Console BigQuery interface")
    print("  • Using the BigQuery client library in Python")
    print("  • Using bq command line tool")

if __name__ == '__main__':
    main()
