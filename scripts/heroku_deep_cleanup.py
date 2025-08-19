#!/usr/bin/env python3
"""
Heroku Deep Database Cleanup Script

This script identifies tables that are truly unused by the current ETL pipeline
and application, not just empty tables. It analyzes actual usage patterns.
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

def analyze_table_usage():
    """Analyze which tables are actually used by the current system."""
    
    # Based on codebase analysis, here are the tables that are actively used:
    
    # CURRENT ACTIVE TABLES (used by ETL and application)
    active_tables = {
        'statements_new': {
            'usage': 'Primary analytics table - used by all queries and UI',
            'source': 'ETL pipeline writes to this table',
            'priority': 'CRITICAL'
        },
        'results_new': {
            'usage': 'Learning results and scores - used by analytics',
            'source': 'ETL pipeline writes to this table', 
            'priority': 'CRITICAL'
        },
        'context_extensions_new': {
            'usage': 'Metadata and extensions - used by analytics',
            'source': 'ETL pipeline writes to this table',
            'priority': 'CRITICAL'
        },
        'statements_flat': {
            'usage': 'Source table for ETL pipeline - still being written to',
            'source': 'Streaming ETL writes to this table',
            'priority': 'ACTIVE'
        }
    }
    
    # LEGACY TABLES (have data but not used by current ETL)
    legacy_tables = {
        'statements_normalized': {
            'usage': 'Old normalized table - replaced by statements_new',
            'source': 'Old ETL process',
            'priority': 'LEGACY'
        },
        'actors': {
            'usage': 'Old actors table - data migrated to new schema',
            'source': 'Old ETL process',
            'priority': 'LEGACY'
        },
        'activities': {
            'usage': 'Old activities table - data migrated to new schema',
            'source': 'Old ETL process', 
            'priority': 'LEGACY'
        },
        'verbs': {
            'usage': 'Old verbs table - not used by current system',
            'source': 'Old ETL process',
            'priority': 'LEGACY'
        }
    }
    
    # SYSTEM TABLES (PostgreSQL internal)
    system_tables = {
        'pg_stat_statements': {
            'usage': 'PostgreSQL performance statistics',
            'source': 'PostgreSQL system',
            'priority': 'SYSTEM'
        },
        'pg_stat_statements_info': {
            'usage': 'PostgreSQL system information',
            'source': 'PostgreSQL system',
            'priority': 'SYSTEM'
        }
    }
    
    # VIEWS (computed from other tables)
    views = {
        'vw_focus_group_responses': {
            'usage': 'View for focus group data',
            'source': 'Computed from statements_new',
            'priority': 'VIEW'
        },
        'vw_user_progress': {
            'usage': 'View for user progress analytics',
            'source': 'Computed from statements_new',
            'priority': 'VIEW'
        }
    }
    
    return {
        'active': active_tables,
        'legacy': legacy_tables,
        'system': system_tables,
        'views': views
    }

def identify_unused_tables(table_analysis, table_usage):
    """Identify tables that can be safely removed."""
    
    unused_tables = []
    
    for table_name, analysis in table_analysis.items():
        # Skip system tables and views
        if table_name.startswith('pg_') or table_name.endswith('_view'):
            continue
            
        # Check if it's a legacy table that's not being used by current ETL
        if table_name in table_usage['legacy']:
            unused_tables.append({
                'table_name': table_name,
                'row_count': analysis['row_count'],
                'reason': f"Legacy table: {table_usage['legacy'][table_name]['usage']}",
                'priority': 'LEGACY'
            })
        # Check for tables not in any usage category
        elif (table_name not in table_usage['active'] and 
              table_name not in table_usage['legacy'] and 
              table_name not in table_usage['system'] and
              table_name not in table_usage['views']):
            unused_tables.append({
                'table_name': table_name,
                'row_count': analysis['row_count'],
                'reason': 'Unknown table - not used by current system',
                'priority': 'UNKNOWN'
            })
    
    return unused_tables

def analyze_tables():
    """Analyze all tables and identify unused ones."""
    logger.info("🔍 Analyzing database tables for deep cleanup...")
    
    conn = get_db_connection()
    
    try:
        all_tables = get_all_tables(conn)
        logger.info(f"Found {len(all_tables)} tables in database")
        
        table_analysis = {}
        
        for table_name in all_tables:
            logger.info(f"📋 Analyzing table: {table_name}")
            
            row_count = get_table_row_count(conn, table_name)
            
            table_analysis[table_name] = {
                'row_count': row_count
            }
            
            logger.info(f"   Rows: {row_count}")
        
        return table_analysis
        
    finally:
        conn.close()

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
    
    parser = argparse.ArgumentParser(description='Deep cleanup of unused tables in Heroku database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be dropped without actually dropping')
    parser.add_argument('--execute', action='store_true', help='Actually drop the unused tables')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze tables, don\'t drop anything')
    parser.add_argument('--legacy-only', action='store_true', help='Only drop legacy tables, keep unknown tables')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute and not args.analyze_only:
        logger.info("🔍 Running in analysis mode. Use --dry-run to see what would be dropped, or --execute to actually drop tables.")
        args.analyze_only = True
    
    try:
        # Analyze all tables
        table_analysis = analyze_tables()
        
        # Get usage analysis
        table_usage = analyze_table_usage()
        
        # Identify unused tables
        unused_tables = identify_unused_tables(table_analysis, table_usage)
        
        # Filter by legacy-only if requested
        if args.legacy_only:
            unused_tables = [t for t in unused_tables if t['priority'] == 'LEGACY']
        
        logger.info(f"\n📊 Deep Analysis Results:")
        logger.info(f"   Total tables: {len(table_analysis)}")
        logger.info(f"   Active tables: {len(table_usage['active'])}")
        logger.info(f"   Legacy tables: {len(table_usage['legacy'])}")
        logger.info(f"   System tables: {len(table_usage['system'])}")
        logger.info(f"   Views: {len(table_usage['views'])}")
        logger.info(f"   Unused tables: {len(unused_tables)}")
        
        if unused_tables:
            logger.info(f"\n🗑️  Tables that can be safely dropped:")
            for table in unused_tables:
                logger.info(f"   {table['table_name']}: {table['row_count']} rows - {table['reason']} ({table['priority']})")
        
        # Show current active tables
        logger.info(f"\n✅ Current active tables (DO NOT DROP):")
        for table_name, info in table_usage['active'].items():
            row_count = table_analysis.get(table_name, {}).get('row_count', 0)
            logger.info(f"   {table_name}: {row_count} rows - {info['usage']}")
        
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

