#!/usr/bin/env python3
"""
Analyze orphaned database tables in 7taps analytics.
This script identifies tables that exist in the database but are not referenced in the codebase.
"""

import os
import sys
import psycopg2
import logging
from pathlib import Path
from typing import Set, Dict, List
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseAnalyzer:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        
    def get_all_tables(self) -> Set[str]:
        """Get all tables in the database."""
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
    
    def get_table_info(self, table_name: str) -> Dict:
        """Get detailed information about a table."""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get table size
            cursor.execute(f"""
                SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))
            """)
            size = cursor.fetchone()[0]
            
            # Get creation date (approximate)
            cursor.execute(f"""
                SELECT MIN(created_at) FROM {table_name} 
                WHERE created_at IS NOT NULL
            """)
            first_record = cursor.fetchone()[0]
            
            cursor.close()
            
            return {
                'row_count': row_count,
                'size': size,
                'first_record': first_record
            }
        except Exception as e:
            return {
                'row_count': 'Error',
                'size': 'Error', 
                'first_record': 'Error',
                'error': str(e)
            }
        finally:
            conn.close()
    
    def scan_codebase_for_table_references(self) -> Set[str]:
        """Scan the codebase for table name references."""
        referenced_tables = set()
        
        # Direct table name patterns to look for
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'CREATE\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'DROP\s+TABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'table_name\s*=\s*[\'"]([a-zA-Z_][a-zA-Z0-9_]*)[\'"]',
            r'table_name\s+IN\s*\([\'"]([a-zA-Z_][a-zA-Z0-9_]*)[\'"]',
        ]
        
        # Scan Python files
        for py_file in project_root.rglob("*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    referenced_tables.update(matches)
            except Exception as e:
                logger.warning(f"Error reading {py_file}: {e}")
        
        # Scan SQL files
        for sql_file in project_root.rglob("*.sql"):
            try:
                content = sql_file.read_text()
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    referenced_tables.update(matches)
            except Exception as e:
                logger.warning(f"Error reading {sql_file}: {e}")
        
        return referenced_tables
    
    def analyze_tables(self):
        """Main analysis function."""
        logger.info("🔍 Analyzing database tables...")
        
        # Get all tables from database
        all_tables = self.get_all_tables()
        logger.info(f"Found {len(all_tables)} tables in database")
        
        # Get referenced tables from codebase
        referenced_tables = self.scan_codebase_for_table_references()
        logger.info(f"Found {len(referenced_tables)} table references in codebase")
        
        # Identify orphaned tables
        orphaned_tables = all_tables - referenced_tables
        
        # Get table details
        table_details = {}
        for table in all_tables:
            table_details[table] = self.get_table_info(table)
        
        # Print results
        print("\n" + "="*80)
        print("DATABASE TABLE ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total tables in database: {len(all_tables)}")
        print(f"   Tables referenced in code: {len(referenced_tables)}")
        print(f"   Orphaned tables: {len(orphaned_tables)}")
        
        print(f"\n✅ ACTIVE TABLES (referenced in code):")
        for table in sorted(referenced_tables):
            if table in table_details:
                details = table_details[table]
                print(f"   • {table}")
                print(f"     - Rows: {details['row_count']}")
                print(f"     - Size: {details['size']}")
                if details.get('first_record'):
                    print(f"     - First record: {details['first_record']}")
                print()
        
        print(f"\n🗑️  ORPHANED TABLES (not referenced in code):")
        if orphaned_tables:
            for table in sorted(orphaned_tables):
                details = table_details[table]
                print(f"   • {table}")
                print(f"     - Rows: {details['row_count']}")
                print(f"     - Size: {details['size']}")
                if details.get('first_record'):
                    print(f"     - First record: {details['first_record']}")
                if details.get('error'):
                    print(f"     - Error: {details['error']}")
                print()
        else:
            print("   No orphaned tables found!")
        
        print(f"\n📋 ALL TABLES:")
        for table in sorted(all_tables):
            status = "✅" if table in referenced_tables else "🗑️"
            details = table_details[table]
            print(f"   {status} {table} ({details['row_count']} rows, {details['size']})")
        
        # Generate cleanup script
        if orphaned_tables:
            print(f"\n🔧 CLEANUP SCRIPT:")
            print("Run this SQL to drop orphaned tables:")
            print("```sql")
            for table in sorted(orphaned_tables):
                print(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print("```")
        
        print("\n" + "="*80)

def main():
    analyzer = DatabaseAnalyzer()
    analyzer.analyze_tables()

if __name__ == "__main__":
    main()
