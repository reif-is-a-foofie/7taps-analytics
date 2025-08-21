#!/usr/bin/env python3
"""
Analyze schema evolution and identify what tables should exist vs what actually exists.
This helps understand the migration history and what needs to be cleaned up.
"""

import os
import sys
import psycopg2
import logging
from pathlib import Path
from typing import Set, Dict, List, Tuple
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaAnalyzer:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        
    def get_current_tables(self) -> Set[str]:
        """Get all tables currently in the database."""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = {row[0] for row in cursor.fetchall()}
            cursor.close()
            return tables
        finally:
            conn.close()
    
    def extract_tables_from_sql_file(self, file_path: Path) -> Set[str]:
        """Extract table names from a SQL migration file."""
        tables = set()
        try:
            content = file_path.read_text()
            
            # Find CREATE TABLE statements
            create_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            matches = re.findall(create_pattern, content, re.IGNORECASE)
            tables.update(matches)
            
            # Find DROP TABLE statements (to understand what was replaced)
            drop_pattern = r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?([a-zA-Z_][a-zA-Z0-9_]*)'
            drop_matches = re.findall(drop_pattern, content, re.IGNORECASE)
            tables.update(drop_matches)
            
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
        
        return tables
    
    def analyze_schema_evolution(self):
        """Analyze the schema evolution and current state."""
        
        # Get current tables
        current_tables = self.get_current_tables()
        
        # Extract tables from migration files
        migrations_dir = project_root / "migrations"
        schema_files = {
            'normalized_schema': migrations_dir / "create_normalized_schema.sql",
            'proper_schema': migrations_dir / "create_proper_schema.sql"
        }
        
        schema_tables = {}
        for name, file_path in schema_files.items():
            if file_path.exists():
                schema_tables[name] = self.extract_tables_from_sql_file(file_path)
        
        # Define what tables should exist based on current codebase
        expected_tables = {
            'normalized_schema': {
                'actors', 'activities', 'statements', 'results', 'context_extensions'
            },
            'proper_schema': {
                'lessons', 'users', 'questions', 'user_activities', 'user_responses'
            },
            'legacy_tables': {
                'statements_flat', 'statements_new', 'results_new', 'context_extensions_new'
            }
        }
        
        # Categorize current tables
        categorized_tables = {
            'normalized_schema': [],
            'proper_schema': [],
            'legacy_tables': [],
            'orphaned': [],
            'unknown': []
        }
        
        for table in current_tables:
            if table in expected_tables['normalized_schema']:
                categorized_tables['normalized_schema'].append(table)
            elif table in expected_tables['proper_schema']:
                categorized_tables['proper_schema'].append(table)
            elif table in expected_tables['legacy_tables']:
                categorized_tables['legacy_tables'].append(table)
            elif table in ['cohort_members', 'learning_paths', 'sessions', 'cohorts', 'verbs']:
                categorized_tables['orphaned'].append(table)
            else:
                categorized_tables['unknown'].append(table)
        
        # Print analysis
        print("\n" + "="*80)
        print("SCHEMA EVOLUTION ANALYSIS")
        print("="*80)
        
        print(f"\n📋 CURRENT DATABASE STATE:")
        print(f"   Total tables: {len(current_tables)}")
        for category, tables in categorized_tables.items():
            if tables:
                print(f"   {category}: {len(tables)} tables")
        
        print(f"\n🏗️  SCHEMA MIGRATION FILES:")
        for name, tables in schema_tables.items():
            print(f"   {name}: {len(tables)} tables defined")
            for table in sorted(tables):
                print(f"     • {table}")
        
        print(f"\n✅ NORMALIZED SCHEMA TABLES (xAPI approach):")
        for table in sorted(categorized_tables['normalized_schema']):
            print(f"   • {table}")
        
        print(f"\n✅ PROPER SCHEMA TABLES (lesson-based approach):")
        for table in sorted(categorized_tables['proper_schema']):
            print(f"   • {table}")
        
        print(f"\n⚠️  LEGACY TABLES (transitional):")
        for table in sorted(categorized_tables['legacy_tables']):
            print(f"   • {table}")
        
        print(f"\n🗑️  ORPHANED TABLES (should be dropped):")
        for table in sorted(categorized_tables['orphaned']):
            print(f"   • {table}")
        
        if categorized_tables['unknown']:
            print(f"\n❓ UNKNOWN TABLES (need investigation):")
            for table in sorted(categorized_tables['unknown']):
                print(f"   • {table}")
        
        # Generate cleanup recommendations
        print(f"\n🔧 CLEANUP RECOMMENDATIONS:")
        
        # Tables that should definitely be dropped
        definitely_drop = categorized_tables['orphaned']
        if definitely_drop:
            print(f"\n   IMMEDIATE DROPS (orphaned tables):")
            for table in sorted(definitely_drop):
                print(f"     • {table}")
        
        # Tables that might be dropped depending on which schema you're using
        legacy_tables = categorized_tables['legacy_tables']
        if legacy_tables:
            print(f"\n   POTENTIAL DROPS (legacy tables - check usage first):")
            for table in sorted(legacy_tables):
                print(f"     • {table}")
        
        # Schema decision needed
        if categorized_tables['normalized_schema'] and categorized_tables['proper_schema']:
            print(f"\n   ⚠️  SCHEMA CONFLICT DETECTED:")
            print(f"     You have both normalized schema ({len(categorized_tables['normalized_schema'])} tables)")
            print(f"     and proper schema ({len(categorized_tables['proper_schema'])} tables) active.")
            print(f"     You should choose one approach and clean up the other.")
        
        # Generate SQL cleanup script
        if definitely_drop:
            print(f"\n🔧 SQL CLEANUP SCRIPT:")
            print("```sql")
            for table in sorted(definitely_drop):
                print(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print("```")
        
        print("\n" + "="*80)

def main():
    analyzer = SchemaAnalyzer()
    analyzer.analyze_schema_evolution()

if __name__ == "__main__":
    main()
