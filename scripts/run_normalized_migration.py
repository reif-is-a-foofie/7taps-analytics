#!/usr/bin/env python3
"""
Script to run the normalized schema migration and ETL processes.

This script will:
1. Create the new normalized schema
2. Migrate existing xAPI data to the new schema
3. Load CSV focus group data into the new schema
4. Verify the migration
"""

import os
import sys
import asyncio
import psycopg2
import pandas as pd
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DATABASE_URL', 'localhost').split('@')[1].split('/')[0] if '@' in os.getenv('DATABASE_URL', '') else 'localhost',
    'database': os.getenv('DATABASE_URL', 'postgres').split('/')[-1] if '/' in os.getenv('DATABASE_URL', '') else 'postgres',
    'user': os.getenv('DATABASE_URL', 'postgres').split('://')[1].split(':')[0] if '://' in os.getenv('DATABASE_URL', '') else 'postgres',
    'password': os.getenv('DATABASE_URL', '').split(':')[2].split('@')[0] if ':' in os.getenv('DATABASE_URL', '') else '',
    'port': 5432
}

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def read_sql_file(file_path):
    """Read SQL file content."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read SQL file {file_path}: {e}")
        raise

def execute_sql(conn, sql, description):
    """Execute SQL with error handling."""
    try:
        logger.info(f"Executing: {description}")
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        logger.info(f"✅ Successfully executed: {description}")
    except Exception as e:
        logger.error(f"❌ Failed to execute {description}: {e}")
        conn.rollback()
        raise

def create_focus_group_csv_table(conn):
    """Create a temporary table for focus group CSV data."""
    try:
        logger.info("Creating focus group CSV table...")
        
        # Read the CSV file
        csv_file = Path(__file__).parent.parent / "All Response Data - Focus Group - Cleaned - All Response Data - Focus Group - Cleaned.csv"
        df = pd.read_csv(csv_file)
        
        # Create table and insert data
        cursor = conn.cursor()
        
        # Drop table if exists
        cursor.execute("DROP TABLE IF EXISTS focus_group_csv")
        
        # Create table
        create_table_sql = """
        CREATE TABLE focus_group_csv (
            "Learner" VARCHAR(255),
            "Card" TEXT,
            "Card type" VARCHAR(100),
            "Lesson Number" INTEGER,
            "Global Q#" INTEGER,
            "PDF Page #" INTEGER,
            "Response" TEXT
        )
        """
        cursor.execute(create_table_sql)
        
        # Insert data
        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO focus_group_csv ("Learner", "Card", "Card type", "Lesson Number", "Global Q#", "PDF Page #", "Response")
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row['Learner'],
                row['Card'],
                row['Card type'],
                row['Lesson Number'],
                row['Global Q#'],
                row['PDF Page #'],
                row['Response']
            ))
        
        conn.commit()
        cursor.close()
        logger.info(f"✅ Created focus_group_csv table with {len(df)} rows")
        
    except Exception as e:
        logger.error(f"❌ Failed to create focus group CSV table: {e}")
        raise

def verify_migration(conn):
    """Verify the migration was successful."""
    try:
        logger.info("Verifying migration...")
        cursor = conn.cursor()
        
        # Check table counts
        tables = ['actors', 'activities', 'statements', 'results', 'context_extensions']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"📊 {table}: {count} records")
        
        # Check source distribution
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM statements 
            GROUP BY source 
            ORDER BY count DESC
        """)
        sources = cursor.fetchall()
        logger.info("📊 Statement sources:")
        for source, count in sources:
            logger.info(f"   {source}: {count} statements")
        
        # Check focus group responses
        cursor.execute("""
            SELECT COUNT(*) 
            FROM vw_focus_group_responses
        """)
        focus_group_count = cursor.fetchone()[0]
        logger.info(f"📊 Focus group responses: {focus_group_count}")
        
        # Check user progress
        cursor.execute("""
            SELECT COUNT(*) 
            FROM vw_user_progress
        """)
        user_count = cursor.fetchone()[0]
        logger.info(f"📊 Users with progress: {user_count}")
        
        cursor.close()
        logger.info("✅ Migration verification complete")
        
    except Exception as e:
        logger.error(f"❌ Failed to verify migration: {e}")
        raise

def main():
    """Main migration function."""
    logger.info("🚀 Starting normalized schema migration...")
    
    try:
        # Connect to database
        conn = get_db_connection()
        logger.info("✅ Connected to database")
        
        # Step 1: Create normalized schema
        schema_sql = read_sql_file("migrations/create_normalized_schema.sql")
        execute_sql(conn, schema_sql, "Create normalized schema")
        
        # Step 2: Create focus group CSV table
        create_focus_group_csv_table(conn)
        
        # Step 3: Migrate xAPI data
        xapi_sql = read_sql_file("migrations/etl_xapi.sql")
        execute_sql(conn, xapi_sql, "Migrate xAPI data to normalized schema")
        
        # Step 4: Load CSV data
        csv_sql = read_sql_file("migrations/etl_csv.sql")
        execute_sql(conn, csv_sql, "Load CSV focus group data to normalized schema")
        
        # Step 5: Verify migration
        verify_migration(conn)
        
        logger.info("🎉 Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
