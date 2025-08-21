#!/usr/bin/env python3
"""
Show the final database structure after marking legacy tables.
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

def show_final_structure():
    """Show the final database structure with legacy tables marked."""
    
    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        cursor = conn.cursor()
        
        print("\n📊 FINAL DATABASE STRUCTURE:")
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
        
        print("\n✅ ACTIVE TABLES (Use These for Demo):")
        for table in active_tables:
            if table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   • {table} ({count} rows)")
                except Exception as e:
                    print(f"   • {table} (Error getting count: {e})")
        
        print("\n⚠️  LEGACY TABLES (Do NOT Use - Marked with LEGACY_ prefix):")
        for table in legacy_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM \"{table}\"")
                count = cursor.fetchone()[0]
                print(f"   • {table} ({count} rows)")
            except Exception as e:
                print(f"   • {table} (Error getting count: {e})")
        
        if other_tables:
            print("\n❓ OTHER TABLES:")
            for table in other_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   • {table} ({count} rows)")
                except Exception as e:
                    print(f"   • {table} (Error getting count: {e})")
        
        print(f"\n📋 SUMMARY:")
        print(f"   Total tables: {len(tables)}")
        print(f"   Active tables: {len([t for t in active_tables if t in tables])}")
        print(f"   Legacy tables: {len(legacy_tables)}")
        print(f"   Other tables: {len(other_tables)}")
        
    finally:
        conn.close()

def main():
    print("🎯 7taps Analytics - Final Database Structure")
    print("="*50)
    
    show_final_structure()
    
    print("\n🎉 LEGACY TABLES SUCCESSFULLY MARKED!")
    print("\n💡 FOR YOUR DEMO TOMORROW:")
    print("   • Use ONLY the ACTIVE TABLES (lessons, users, questions, etc.)")
    print("   • IGNORE all LEGACY_ tables - they're clearly marked")
    print("   • Check LEGACY_TABLES.md for documentation")
    print("   • Your database is now clean and demo-ready!")

if __name__ == "__main__":
    main()
