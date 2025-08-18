#!/usr/bin/env python3
"""
Cleanup script to drop old tables that are no longer needed.

This script removes tables that were used for the old CSV import process
now that we have the CSV to xAPI converter for unified data pipeline.
"""

import os
import sys
import logging
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.7taps')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
def get_db_config():
    """Parse DATABASE_URL to get connection parameters."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Parse postgresql://user:password@host:port/database
    if database_url.startswith('postgresql://'):
        # Remove postgresql:// prefix
        url = database_url[13:]
        
        # Split user:password@host:port/database
        if '@' in url:
            auth_part, rest = url.split('@', 1)
            if ':' in auth_part:
                user, password = auth_part.split(':', 1)
            else:
                user, password = auth_part, ''
            
            if '/' in rest:
                host_port, database = rest.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host, port = host_port, 5432
            else:
                host, port, database = rest, 5432, 'postgres'
        else:
            # No authentication
            user, password = '', ''
            if '/' in url:
                host_port, database = url.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host, port = host_port, 5432
            else:
                host, port, database = url, 5432, 'postgres'
    else:
        raise ValueError(f"Unsupported database URL format: {database_url}")
    
    return {
        'host': host,
        'database': database,
        'user': user,
        'password': password,
        'port': port
    }

DB_CONFIG = get_db_config()

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def check_table_exists(conn, table_name):
    """Check if a table exists."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        logger.error(f"Error checking if table {table_name} exists: {e}")
        return False

def get_table_row_count(conn, table_name):
    """Get the row count for a table."""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    except Exception as e:
        logger.error(f"Error getting row count for {table_name}: {e}")
        return 0

def drop_table_safely(conn, table_name, dry_run=True):
    """Safely drop a table with confirmation."""
    try:
        if not check_table_exists(conn, table_name):
            logger.info(f"📋 Table {table_name} does not exist, skipping...")
            return True
        
        # Get row count before dropping
        row_count = get_table_row_count(conn, table_name)
        logger.info(f"📊 Table {table_name} has {row_count} rows")
        
        if dry_run:
            logger.info(f"🔍 DRY RUN: Would drop table {table_name}")
            return True
        
        # Confirm with user if table has data
        if row_count > 0:
            response = input(f"⚠️  Table {table_name} has {row_count} rows. Are you sure you want to drop it? (yes/no): ")
            if response.lower() != 'yes':
                logger.info(f"❌ Skipping drop of {table_name}")
                return False
        
        # Drop the table
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Successfully dropped table {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error dropping table {table_name}: {e}")
        return False

def cleanup_old_tables(dry_run=True):
    """Clean up old tables that are no longer needed."""
    
    logger.info("🧹 Starting cleanup of old tables...")
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No tables will actually be dropped")
    
    # Tables that can be safely dropped
    tables_to_drop = [
        # Old CSV import tables
        "focus_group_csv",
        
        # Old normalized tables (replaced by statements_new, results_new, context_extensions_new)
        "statements",           # Old normalized statements table
        "results",             # Old normalized results table  
        "context_extensions",  # Old normalized context extensions table
        "actors",              # Old normalized actors table
        "activities",          # Old normalized activities table
        
        # Old flat table (if data has been migrated)
        "statements_flat",     # Original flat table - BE CAREFUL!
        
        # Old normalized tables from data_normalization.py
        "statements_normalized",
        "verbs"
    ]
    
    conn = get_db_connection()
    
    try:
        dropped_count = 0
        skipped_count = 0
        
        for table_name in tables_to_drop:
            logger.info(f"\n📋 Processing table: {table_name}")
            
            if drop_table_safely(conn, table_name, dry_run):
                dropped_count += 1
            else:
                skipped_count += 1
        
        logger.info(f"\n📊 Cleanup Summary:")
        logger.info(f"   Tables processed: {len(tables_to_drop)}")
        logger.info(f"   Tables dropped: {dropped_count}")
        logger.info(f"   Tables skipped: {skipped_count}")
        
        if dry_run:
            logger.info("\n🔍 This was a dry run. Run with --execute to actually drop tables.")
        else:
            logger.info("\n✅ Cleanup completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        raise
    finally:
        conn.close()

def verify_current_schema():
    """Verify the current schema after cleanup."""
    
    logger.info("\n🔍 Verifying current schema...")
    
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Check which tables still exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%statement%' 
            OR table_name LIKE '%result%' 
            OR table_name LIKE '%context%'
            OR table_name LIKE '%actor%'
            OR table_name LIKE '%activity%'
            ORDER BY table_name
        """)
        
        remaining_tables = cursor.fetchall()
        
        logger.info("📋 Remaining tables:")
        for (table_name,) in remaining_tables:
            count = get_table_row_count(conn, table_name)
            logger.info(f"   {table_name}: {count} rows")
        
        # Check if new normalized tables exist
        new_tables = ['statements_new', 'results_new', 'context_extensions_new']
        for table in new_tables:
            if check_table_exists(conn, table):
                count = get_table_row_count(conn, table)
                logger.info(f"✅ {table}: {count} rows")
            else:
                logger.warning(f"⚠️  {table}: NOT FOUND")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"❌ Error verifying schema: {e}")
        raise
    finally:
        conn.close()

def main():
    """Main cleanup function."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up old database tables")
    parser.add_argument("--execute", action="store_true", help="Actually execute the cleanup (default is dry run)")
    parser.add_argument("--verify", action="store_true", help="Verify current schema after cleanup")
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    logger.info("🚀 Starting Database Table Cleanup")
    logger.info("=" * 50)
    
    try:
        # Run cleanup
        cleanup_old_tables(dry_run=dry_run)
        
        # Verify schema if requested
        if args.verify:
            verify_current_schema()
        
        logger.info("\n🎉 Cleanup process completed!")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
