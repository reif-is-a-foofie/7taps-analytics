#!/usr/bin/env python3
"""
Fix partitioning issues and complete the migration
"""

import os
import sys
import pandas as pd
import psycopg2
from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core import exceptions as google_exceptions

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

def fix_table_partitioning(table_name):
    """Fix partitioning for a table by recreating it without partitioning."""
    print(f"🔧 Fixing partitioning for {table_name}...")
    
    bq_client = get_bigquery_client()
    table_ref = bq_client.dataset("taps_data").table(table_name)
    
    try:
        # Delete the existing table
        bq_client.delete_table(table_ref)
        print(f"   🗑️  Deleted existing table {table_name}")
    except google_exceptions.NotFound:
        print(f"   ℹ️  Table {table_name} doesn't exist yet")
    except Exception as e:
        print(f"   ⚠️  Could not delete table {table_name}: {e}")

def migrate_table_without_partitioning(table_name):
    """Migrate a table without partitioning."""
    print(f"🔄 Migrating {table_name} (without partitioning)...")
    
    try:
        # Get data from Heroku
        with get_heroku_connection() as conn:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            print(f"   📊 Retrieved {len(df)} rows")
        
        if len(df) == 0:
            print(f"   ⚠️  No data to migrate for {table_name}")
            return
        
        # Upload to BigQuery without partitioning
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
    print("🚀 Fixing Partitioning and Completing Migration")
    print("=" * 60)
    
    # Tables that had partitioning issues
    problematic_tables = ["user_activities", "user_responses"]
    
    for table in problematic_tables:
        fix_table_partitioning(table)
        migrate_table_without_partitioning(table)
    
    print("\n" + "=" * 60)
    print("🎉 Migration Complete!")
    print("=" * 60)
    
    # Verify all tables
    print("\n📊 Verifying migrated data...")
    bq_client = get_bigquery_client()
    
    all_tables = ["users", "lessons", "questions", "user_activities", "user_responses"]
    total_rows = 0
    
    for table in all_tables:
        try:
            table_ref = bq_client.dataset("taps_data").table(table)
            table_obj = bq_client.get_table(table_ref)
            row_count = table_obj.num_rows
            print(f"   ✅ {table}: {row_count} rows")
            total_rows += row_count
        except Exception as e:
            print(f"   ❌ {table}: Error - {e}")
    
    print(f"\n📈 Total rows migrated: {total_rows}")

if __name__ == '__main__':
    main()
