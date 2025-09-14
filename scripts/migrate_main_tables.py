#!/usr/bin/env python3
"""
Simple migration script for main tables from Heroku to BigQuery
"""

import os
import sys
import pandas as pd
import psycopg2
from google.cloud import bigquery
from google.oauth2 import service_account

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_heroku_connection():
    """Get connection to Heroku PostgreSQL database."""
    return psycopg2.connect(
        host="c5cnr847jq0fj3.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
        database="d7s5ke2hmuqipn",
        user="u19o5qm786p1d1",
        password="p952c21ce2372a85402c0253505bb3f892f49f149b27cce81e5f44b558b98f4c2",
        port="5432"
    )

def get_bigquery_client():
    """Get BigQuery client."""
    key_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'google-cloud-key.json')
    credentials = service_account.Credentials.from_service_account_file(key_file)
    return bigquery.Client(credentials=credentials, project="taps-data")

def migrate_table(table_name):
    """Migrate a single table."""
    print(f"🔄 Migrating {table_name}...")
    
    try:
        # Get data from Heroku
        with get_heroku_connection() as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            print(f"   📊 Retrieved {len(df)} rows")
        
        if len(df) == 0:
            print(f"   ⚠️  No data to migrate for {table_name}")
            return
        
        # Upload to BigQuery
        bq_client = get_bigquery_client()
        table_ref = bq_client.dataset("taps_data").table(table_name)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE"  # Replace existing data
        )
        
        job = bq_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for job to complete
        
        print(f"   ✅ Successfully migrated {len(df)} rows to BigQuery")
        
    except Exception as e:
        print(f"   ❌ Failed to migrate {table_name}: {e}")

def main():
    """Main migration function."""
    print("🚀 Starting Main Tables Migration")
    print("=" * 50)
    
    # Main tables to migrate (excluding LEGACY tables)
    main_tables = ["users", "lessons", "questions", "user_activities", "user_responses"]
    
    for table in main_tables:
        migrate_table(table)
    
    print("\n" + "=" * 50)
    print("🎉 Migration Complete!")
    print("=" * 50)

if __name__ == '__main__':
    main()
