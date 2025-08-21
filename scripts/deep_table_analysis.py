#!/usr/bin/env python3
"""
Deep analysis of database tables to identify ALL tables that should be removed.
This includes orphaned tables, tables with schema issues, and deprecated tables.
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

class DeepTableAnalyzer:
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
    
    def get_table_schema(self, table_name: str) -> Dict:
        """Get detailed schema information about a table."""
        conn = psycopg2.connect(self.db_url)
        try:
            cursor = conn.cursor()
            
            # Get column information
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
            except Exception as e:
                row_count = f"Error: {str(e)}"
            
            # Get table size
            try:
                cursor.execute(f"""
                    SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))
                """)
                size = cursor.fetchone()[0]
            except Exception as e:
                size = f"Error: {str(e)}"
            
            # Check for created_at column
            has_created_at = any(col[0] == 'created_at' for col in columns)
            
            # Get first record if created_at exists
            first_record = None
            if has_created_at:
                try:
                    cursor.execute(f"""
                        SELECT MIN(created_at) FROM {table_name} 
                        WHERE created_at IS NOT NULL
                    """)
                    first_record = cursor.fetchone()[0]
                except Exception as e:
                    first_record = f"Error: {str(e)}"
            
            cursor.close()
            
            return {
                'columns': columns,
                'row_count': row_count,
                'size': size,
                'has_created_at': has_created_at,
                'first_record': first_record,
                'column_count': len(columns)
            }
        except Exception as e:
            return {
                'error': str(e),
                'columns': [],
                'row_count': 'Error',
                'size': 'Error',
                'has_created_at': False,
                'first_record': 'Error',
                'column_count': 0
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
    
    def categorize_tables(self, all_tables: Set[str], referenced_tables: Set[str]) -> Dict[str, List[str]]:
        """Categorize tables based on various criteria."""
        categories = {
            'active': [],
            'orphaned': [],
            'deprecated': [],
            'problematic': [],
            'empty': []
        }
        
        for table in all_tables:
            schema_info = self.get_table_schema(table)
            
            # Check if table has errors
            if 'error' in schema_info:
                categories['problematic'].append(table)
                continue
            
            # Check if table is empty
            if schema_info['row_count'] == 0:
                categories['empty'].append(table)
            
            # Check if table is referenced in code
            if table in referenced_tables:
                categories['active'].append(table)
            else:
                # Check for deprecated naming patterns
                if any(pattern in table for pattern in ['_old', '_backup', '_temp', '_flat']):
                    categories['deprecated'].append(table)
                else:
                    categories['orphaned'].append(table)
        
        return categories
    
    def analyze_tables(self):
        """Main analysis function."""
        logger.info("🔍 Performing deep table analysis...")
        
        # Get all tables from database
        all_tables = self.get_all_tables()
        logger.info(f"Found {len(all_tables)} tables in database")
        
        # Get referenced tables from codebase
        referenced_tables = self.scan_codebase_for_table_references()
        logger.info(f"Found {len(referenced_tables)} table references in codebase")
        
        # Categorize tables
        categories = self.categorize_tables(all_tables, referenced_tables)
        
        # Print results
        print("\n" + "="*80)
        print("DEEP DATABASE TABLE ANALYSIS REPORT")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total tables in database: {len(all_tables)}")
        print(f"   Active tables: {len(categories['active'])}")
        print(f"   Orphaned tables: {len(categories['orphaned'])}")
        print(f"   Deprecated tables: {len(categories['deprecated'])}")
        print(f"   Problematic tables: {len(categories['problematic'])}")
        print(f"   Empty tables: {len(categories['empty'])}")
        
        print(f"\n✅ ACTIVE TABLES (referenced in code):")
        for table in sorted(categories['active']):
            schema_info = self.get_table_schema(table)
            print(f"   • {table}")
            print(f"     - Rows: {schema_info['row_count']}")
            print(f"     - Size: {schema_info['size']}")
            print(f"     - Columns: {schema_info['column_count']}")
            if schema_info.get('first_record'):
                print(f"     - First record: {schema_info['first_record']}")
            print()
        
        print(f"\n🗑️  ORPHANED TABLES (not referenced in code):")
        for table in sorted(categories['orphaned']):
            schema_info = self.get_table_schema(table)
            print(f"   • {table}")
            print(f"     - Rows: {schema_info['row_count']}")
            print(f"     - Size: {schema_info['size']}")
            print(f"     - Columns: {schema_info['column_count']}")
            if schema_info.get('first_record'):
                print(f"     - First record: {schema_info['first_record']}")
            print()
        
        print(f"\n⚠️  DEPRECATED TABLES (old naming patterns):")
        for table in sorted(categories['deprecated']):
            schema_info = self.get_table_schema(table)
            print(f"   • {table}")
            print(f"     - Rows: {schema_info['row_count']}")
            print(f"     - Size: {schema_info['size']}")
            print(f"     - Columns: {schema_info['column_count']}")
            if schema_info.get('first_record'):
                print(f"     - First record: {schema_info['first_record']}")
            print()
        
        print(f"\n❌ PROBLEMATIC TABLES (schema errors):")
        for table in sorted(categories['problematic']):
            schema_info = self.get_table_schema(table)
            print(f"   • {table}")
            print(f"     - Error: {schema_info.get('error', 'Unknown error')}")
            print()
        
        print(f"\n📋 EMPTY TABLES (0 rows):")
        for table in sorted(categories['empty']):
            schema_info = self.get_table_schema(table)
            print(f"   • {table} ({schema_info['size']}, {schema_info['column_count']} columns)")
        
        # Generate comprehensive cleanup script
        tables_to_drop = categories['orphaned'] + categories['deprecated'] + categories['problematic']
        
        if tables_to_drop:
            print(f"\n🔧 COMPREHENSIVE CLEANUP SCRIPT:")
            print("Run this SQL to drop all unnecessary tables:")
            print("```sql")
            for table in sorted(tables_to_drop):
                print(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print("```")
            
            print(f"\n📝 CLEANUP SUMMARY:")
            print(f"   Tables to drop: {len(tables_to_drop)}")
            print(f"   Orphaned: {len(categories['orphaned'])}")
            print(f"   Deprecated: {len(categories['deprecated'])}")
            print(f"   Problematic: {len(categories['problematic'])}")
        
        print("\n" + "="*80)

def main():
    analyzer = DeepTableAnalyzer()
    analyzer.analyze_tables()

if __name__ == "__main__":
    main()
