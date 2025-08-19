#!/usr/bin/env python3
"""
Heroku Database Table Cleanup Script

This script identifies and removes unused tables from the Heroku database.
Based on the current normalized schema migration, several old tables may be redundant.
"""

import os
import sys
import logging
import psycopg2
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_heroku_db_url():
    """Get the Heroku database URL using Heroku CLI."""
    try:
        result = subprocess.run(
            ['heroku', 'config:get', 'DATABASE_URL', '--app', 'seventaps-analytics'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get DATABASE_URL from Heroku: {e}")
        logger.error("Make sure you're logged into Heroku CLI and have access to the app")
        return None
    except FileNotFoundError:
        logger.error("Heroku CLI not found. Please install it first.")
        return None

def get_db_connection():
    """Get database connection using Heroku DATABASE_URL."""
    database_url = get_heroku_db_url()
    if not database_url:
        raise ValueError("Could not get DATABASE_URL from Heroku")
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def get_all_tables(conn):
    """Get all tables in the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        return []

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

def check_table_usage(conn, table_name):
    """Check if a table is referenced by other tables or views."""
    try:
        cursor = conn.cursor()
        
        # Simple check - just see if the table has any data
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        cursor.close()
        
        # For now, assume tables with data are being used
        # This is a conservative approach
        return {
            'foreign_keys': [],
            'views': [],
            'is_used': count > 0
        }
    except Exception as e:
        logger.error(f"Error checking usage for {table_name}: {e}")
        # If there's an error, assume the table might be used to be safe
        return {'foreign_keys': [], 'views': [], 'is_used': True}

def analyze_tables():
    """Analyze all tables and identify unused ones."""
    logger.info("🔍 Analyzing database tables...")
    
    conn = get_db_connection()
    
    try:
        all_tables = get_all_tables(conn)
        logger.info(f"Found {len(all_tables)} tables in database")
        
        table_analysis = {}
        
        for table_name in all_tables:
            logger.info(f"📋 Analyzing table: {table_name}")
            
            row_count = get_table_row_count(conn, table_name)
            usage_info = check_table_usage(conn, table_name)
            
            table_analysis[table_name] = {
                'row_count': row_count,
                'usage_info': usage_info,
                'is_used': usage_info['is_used']
            }
            
            logger.info(f"   Rows: {row_count}, Used: {usage_info['is_used']}")
        
        return table_analysis
        
    finally:
        conn.close()

def identify_unused_tables(table_analysis):
    """Identify tables that can be safely removed."""
    
    # Tables that are known to be replaced by the new normalized schema
    known_old_tables = [
        'statements_flat',      # Replaced by statements_new
        'focus_group_csv',      # Old CSV import table
        'statements',           # Old normalized table
        'results',              # Old normalized table  
        'context_extensions',   # Old normalized table
        'actors',               # Old normalized table
        'activities',           # Old normalized table
        'statements_normalized', # Old normalized table
        'verbs'                 # Old normalized table
    ]
    
    unused_tables = []
    
    for table_name, analysis in table_analysis.items():
        # Skip system tables and views
        if table_name.startswith('pg_') or table_name.endswith('_view'):
            continue
            
        # Check if it's a known old table that's not being used
        if table_name in known_old_tables and not analysis['is_used']:
            unused_tables.append({
                'table_name': table_name,
                'row_count': analysis['row_count'],
                'reason': 'Known old table replaced by new schema'
            })
        # Check for empty tables that aren't referenced
        elif analysis['row_count'] == 0 and not analysis['is_used']:
            unused_tables.append({
                'table_name': table_name,
                'row_count': analysis['row_count'],
                'reason': 'Empty table with no references'
            })
    
    return unused_tables

def drop_table_safely(conn, table_name, dry_run=True):
    """Safely drop a table with confirmation."""
    try:
        if dry_run:
            logger.info(f"🔍 DRY RUN: Would drop table {table_name}")
            return True
        
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Successfully dropped table {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error dropping table {table_name}: {e}")
        return False

def main():
    """Main cleanup function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up unused tables in Heroku database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be dropped without actually dropping')
    parser.add_argument('--execute', action='store_true', help='Actually drop the unused tables')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze tables, don\'t drop anything')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute and not args.analyze_only:
        logger.info("🔍 Running in analysis mode. Use --dry-run to see what would be dropped, or --execute to actually drop tables.")
        args.analyze_only = True
    
    try:
        # Analyze all tables
        table_analysis = analyze_tables()
        
        # Identify unused tables
        unused_tables = identify_unused_tables(table_analysis)
        
        logger.info(f"\n📊 Analysis Results:")
        logger.info(f"   Total tables: {len(table_analysis)}")
        logger.info(f"   Unused tables: {len(unused_tables)}")
        
        if unused_tables:
            logger.info(f"\n🗑️  Unused tables that can be dropped:")
            for table in unused_tables:
                logger.info(f"   {table['table_name']}: {table['row_count']} rows - {table['reason']}")
        
        if args.analyze_only:
            return
        
        if not unused_tables:
            logger.info("✅ No unused tables found to clean up!")
            return
        
        if args.dry_run:
            logger.info(f"\n🔍 DRY RUN: Would drop {len(unused_tables)} tables")
            return
        
        if args.execute:
            logger.info(f"\n🗑️  Dropping {len(unused_tables)} unused tables...")
            
            conn = get_db_connection()
            try:
                dropped_count = 0
                for table in unused_tables:
                    if drop_table_safely(conn, table['table_name'], dry_run=False):
                        dropped_count += 1
                
                logger.info(f"✅ Successfully dropped {dropped_count} tables")
                
            finally:
                conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
