#!/usr/bin/env python3
"""
Script to import focus group data and fix the data pipeline.

This script will:
1. Import the focus group CSV data
2. Trigger migration of existing flat statements
3. Verify the data pipeline is working
"""

import os
import sys
import asyncio
import json
import requests
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent.parent / "app"))

from app.data_normalization import DataNormalizer
from app.migrate_flat_to_normalized import migrate_flat_to_normalized

# Heroku app URL
HEROKU_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

async def import_focus_group_data():
    """Import focus group data from CSV file."""
    try:
        # Read the CSV file
        csv_file = Path(__file__).parent.parent / "All Response Data - Focus Group - Cleaned - All Response Data - Focus Group - Cleaned.csv"
        
        if not csv_file.exists():
            print(f"❌ CSV file not found: {csv_file}")
            return False
        
        print(f"📁 Reading CSV file: {csv_file}")
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_data = f.read()
        
        # Import via API
        print("🚀 Importing focus group data via API...")
        response = requests.post(
            f"{HEROKU_URL}/api/import/focus-group",
            json={
                "csv_data": csv_data,
                "cohort_name": "focus_group_2024_immediate"
            },
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Focus group import successful!")
            print(f"   - Imported: {result['imported_count']} records")
            print(f"   - Errors: {result['error_count']}")
            print(f"   - Cohort ID: {result['cohort_id']}")
            return True
        else:
            print(f"❌ Focus group import failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error importing focus group data: {e}")
        return False

async def trigger_migration():
    """Trigger migration of existing flat statements."""
    try:
        print("🔄 Triggering migration of existing flat statements...")
        response = requests.post(
            f"{HEROKU_URL}/api/migration/trigger",
            json={"force": True},
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Migration triggered successfully!")
            print(f"   - Status: {result['status']}")
            print(f"   - Total statements: {result['total_statements']}")
            return True
        else:
            print(f"❌ Migration trigger failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error triggering migration: {e}")
        return False

async def check_migration_status():
    """Check migration status."""
    try:
        print("📊 Checking migration status...")
        response = requests.get(f"{HEROKU_URL}/api/migration/status", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"📈 Migration Status:")
            print(f"   - Status: {result['status']}")
            print(f"   - Progress: {result['progress_percentage']:.1f}%")
            print(f"   - Migrated: {result['migrated_count']}")
            print(f"   - Errors: {result['error_count']}")
            return result
        else:
            print(f"❌ Failed to get migration status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking migration status: {e}")
        return None

async def check_cohort_analytics():
    """Check cohort analytics."""
    try:
        print("📊 Checking cohort analytics...")
        response = requests.get(f"{HEROKU_URL}/api/analytics/cohorts", timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"📈 Cohort Analytics:")
            print(f"   - Total cohorts: {result['total_cohorts']}")
            for cohort in result['cohorts']:
                print(f"   - {cohort['cohort_id']}: {cohort['total_learners']} learners, {cohort['total_responses']} responses")
            return result
        else:
            print(f"❌ Failed to get cohort analytics: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking cohort analytics: {e}")
        return None

async def main():
    """Main function to run the complete data pipeline fix."""
    print("🚀 Starting data pipeline fix...")
    print("=" * 50)
    
    # Step 1: Import focus group data
    print("\n1️⃣ Importing focus group data...")
    import_success = await import_focus_group_data()
    
    if not import_success:
        print("❌ Focus group import failed. Stopping.")
        return
    
    # Step 2: Trigger migration
    print("\n2️⃣ Triggering migration...")
    migration_triggered = await trigger_migration()
    
    if not migration_triggered:
        print("❌ Migration trigger failed. Stopping.")
        return
    
    # Step 3: Monitor migration progress
    print("\n3️⃣ Monitoring migration progress...")
    for i in range(10):  # Check 10 times
        await asyncio.sleep(5)  # Wait 5 seconds between checks
        status = await check_migration_status()
        
        if status and status['status'] == 'completed':
            print("✅ Migration completed!")
            break
        elif status and status['status'] == 'running':
            print(f"⏳ Migration in progress: {status['progress_percentage']:.1f}%")
        else:
            print("⏳ Waiting for migration to start...")
    
    # Step 4: Check final results
    print("\n4️⃣ Checking final results...")
    await check_cohort_analytics()
    
    print("\n🎉 Data pipeline fix completed!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
