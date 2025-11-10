#!/usr/bin/env python3
"""
Script to sync cohorts from users table to cohorts table.
Can be run manually or triggered after CSV imports.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.cohort_sync import get_cohort_sync_service

async def main():
    print("🔄 Syncing cohorts from users table to cohorts table...")
    
    service = get_cohort_sync_service()
    result = await service.sync_cohorts_from_users()
    
    if result.get("success"):
        print(f"✅ Successfully synced {result.get('synced_count', 0)} cohorts")
        for cohort in result.get("cohorts", []):
            print(f"   - {cohort['cohort_name']}: {cohort['user_count']} users, {cohort['statement_count']} statements")
    else:
        print(f"❌ Failed to sync cohorts: {result.get('error')}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

