#!/usr/bin/env python3
"""
Mark legacy tables with clear naming convention and documentation.
This script renames legacy tables with a 'LEGACY_' prefix and adds comments.
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

def mark_legacy_tables():
    """Rename legacy tables with LEGACY_ prefix and add documentation."""
    
    # Legacy tables to mark
    legacy_tables = [
        'statements_new',
        'results_new', 
        'context_extensions_new',
        'statements_flat',
        'statements_normalized',
        'activities',
        'actors'
    ]
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        cursor = conn.cursor()
        
        print("🏷️  Marking legacy tables...")
        print("="*50)
        
        marked_tables = []
        for table in legacy_tables:
            try:
                # Check if table exists
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                """)
                
                if cursor.fetchone()[0] == 0:
                    print(f"   ⏭️  Table '{table}' does not exist, skipping...")
                    continue
                
                # Check if already marked
                if table.startswith('LEGACY_'):
                    print(f"   ⏭️  Table '{table}' already marked, skipping...")
                    continue
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                # Rename table with LEGACY_ prefix
                new_name = f"LEGACY_{table}"
                cursor.execute(f'ALTER TABLE "{table}" RENAME TO "{new_name}"')
                
                # Add comment to the table
                comment = f"LEGACY TABLE: {table} - This table is deprecated and should not be used for new development. Contains {row_count} rows."
                cursor.execute(f'COMMENT ON TABLE "{new_name}" IS %s', (comment,))
                
                marked_tables.append((table, new_name, row_count))
                print(f"   ✅ Marked '{table}' → '{new_name}' ({row_count} rows)")
                
            except Exception as e:
                print(f"   ❌ Error marking '{table}': {e}")
        
        conn.commit()
        
        if marked_tables:
            print(f"\n✅ Successfully marked {len(marked_tables)} tables:")
            for old_name, new_name, row_count in marked_tables:
                print(f"   • {old_name} → {new_name} ({row_count} rows)")
        else:
            print("\n✅ No tables needed to be marked.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Marking failed: {e}")
        raise
    finally:
        conn.close()

def create_legacy_documentation():
    """Create documentation file for legacy tables."""
    
    legacy_docs = """# Legacy Tables Documentation

## Overview
These tables are marked with the `LEGACY_` prefix and should **NOT** be used for new development.

## Legacy Tables

### LEGACY_statements_new
- **Original name:** statements_new
- **Purpose:** Transitional table from flat to normalized schema
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` and `user_responses` tables

### LEGACY_results_new  
- **Original name:** results_new
- **Purpose:** Transitional results table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_responses` table

### LEGACY_context_extensions_new
- **Original name:** context_extensions_new
- **Purpose:** Transitional context extensions table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Data is now in `lessons`, `questions`, and `user_activities` tables

### LEGACY_statements_flat
- **Original name:** statements_flat
- **Purpose:** Original flat xAPI statements storage
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` table

### LEGACY_statements_normalized
- **Original name:** statements_normalized
- **Purpose:** Attempted normalized xAPI schema
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `user_activities` table

### LEGACY_activities
- **Original name:** activities
- **Purpose:** xAPI activities table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `lessons` and `questions` tables

### LEGACY_actors
- **Original name:** actors
- **Purpose:** xAPI actors table
- **Status:** DEPRECATED - Use proper schema tables instead
- **Replacement:** Use `users` table

## Current Active Schema

### Primary Tables (Use These)
- `lessons` - Main lesson entities
- `users` - Normalized user data  
- `questions` - Questions within lessons
- `user_activities` - All user interactions
- `user_responses` - Specific question responses

### How to Query
```sql
-- Instead of LEGACY tables, use:
SELECT * FROM user_activities;  -- instead of LEGACY_statements_new
SELECT * FROM user_responses;   -- instead of LEGACY_results_new
SELECT * FROM lessons;          -- instead of LEGACY_activities
SELECT * FROM users;            -- instead of LEGACY_actors
```

## Migration Notes
- Legacy tables contain historical data that may be migrated to proper schema
- Do not create new queries using LEGACY_ tables
- Legacy tables can be dropped after confirming data migration
"""
    
    docs_path = project_root / "LEGACY_TABLES.md"
    docs_path.write_text(legacy_docs)
    print(f"\n📝 Created documentation: {docs_path}")

def show_current_structure():
    """Show the current database structure with legacy tables marked."""
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        cursor = conn.cursor()
        
        print("\n📊 CURRENT DATABASE STRUCTURE:")
        print("="*50)
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Categorize tables
        active_tables = ['lessons', 'users', 'questions', 'user_activities', 'user_responses']
        legacy_tables = [t for t in tables if t.startswith('LEGACY_')]
        other_tables = [t for t in tables if t not in active_tables and not t.startswith('LEGACY_')]
        
        print("\n✅ ACTIVE TABLES (Use These):")
        for table in active_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table} ({count} rows)")
        
        print("\n⚠️  LEGACY TABLES (Do NOT Use):")
        for table in legacy_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   • {table} ({count} rows)")
        
        if other_tables:
            print("\n❓ OTHER TABLES:")
            for table in other_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   • {table} ({count} rows)")
        
    finally:
        conn.close()

def main():
    print("🏷️  7taps Analytics - Legacy Table Marking")
    print("="*50)
    
    # Step 1: Mark legacy tables
    print("\n📋 STEP 1: Mark legacy tables with LEGACY_ prefix")
    mark_legacy_tables()
    
    # Step 2: Create documentation
    print("\n📋 STEP 2: Create legacy tables documentation")
    create_legacy_documentation()
    
    # Step 3: Show current structure
    print("\n📋 STEP 3: Show current database structure")
    show_current_structure()
    
    print("\n🎉 LEGACY TABLE MARKING COMPLETE!")
    print("\n💡 BENEFITS:")
    print("   • Clear visual distinction between active and legacy tables")
    print("   • Documentation explains what each legacy table was for")
    print("   • Easy to identify which tables to avoid in new queries")
    print("   • Can safely drop LEGACY_ tables later when ready")

if __name__ == "__main__":
    main()
