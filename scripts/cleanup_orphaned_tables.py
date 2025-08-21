#!/usr/bin/env python3
"""
Safely drop orphaned database tables in 7taps analytics.
This script drops tables that are not referenced in the codebase.
"""

import os
import sys
import psycopg2
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_orphaned_tables():
    """Drop orphaned tables that are not referenced in the codebase."""
    
    # These tables were identified as orphaned by analyze_orphaned_tables.py
    orphaned_tables = [
        'cohort_members',
        'learning_paths', 
        'sessions'
    ]
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        cursor = conn.cursor()
        
        print("🗑️  Cleaning up orphaned tables...")
        print("="*50)
        
        for table in orphaned_tables:
            try:
                # Check if table exists and get its info
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                """)
                
                if cursor.fetchone()[0] == 0:
                    print(f"   ⏭️  Table '{table}' does not exist, skipping...")
                    continue
                
                # Get row count before dropping
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                if row_count > 0:
                    print(f"   ⚠️  WARNING: Table '{table}' has {row_count} rows!")
                    response = input(f"   Are you sure you want to drop '{table}'? (y/N): ")
                    if response.lower() != 'y':
                        print(f"   ⏭️  Skipping '{table}'...")
                        continue
                
                # Drop the table
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"   ✅ Dropped table '{table}' ({row_count} rows)")
                
            except Exception as e:
                print(f"   ❌ Error dropping table '{table}': {e}")
        
        conn.commit()
        print("\n✅ Cleanup completed successfully!")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Cleanup failed: {e}")
        raise
    finally:
        conn.close()

def main():
    print("🧹 7taps Analytics - Orphaned Table Cleanup")
    print("="*50)
    print("This script will drop the following orphaned tables:")
    print("   • cohort_members")
    print("   • learning_paths") 
    print("   • sessions")
    print()
    print("These tables are not referenced in the codebase and can be safely removed.")
    print()
    
    response = input("Proceed with cleanup? (y/N): ")
    if response.lower() == 'y':
        cleanup_orphaned_tables()
    else:
        print("Cleanup cancelled.")

if __name__ == "__main__":
    main()
