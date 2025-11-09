#!/usr/bin/env python3
"""
Import UVM Users CSV into BigQuery users table.

This script imports user data from the UVM Users CSV file and stores it
in the BigQuery users table with proper normalization.
"""

import sys
import asyncio
import csv
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.csv_import_service import CSVImportService
from app.services.user_normalization import get_user_normalization_service
from app.config.gcp_config import get_gcp_config
from app.logging_config import get_logger

logger = get_logger("uvm_import")


async def import_uvm_users(csv_file_path: str):
    """Import UVM users from CSV file."""
    try:
        # Read CSV file
        logger.info(f"Reading CSV file: {csv_file_path}")
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Use CSV import service
        csv_service = CSVImportService()
        result = await csv_service.import_csv_data(csv_content, "UVM Users.csv")
        
        if result["success"]:
            logger.info(f"✅ Successfully imported {result['imported_count']} users")
            print(f"\n✅ Import successful!")
            print(f"   Imported: {result['imported_count']} users")
            print(f"   Total rows: {result['total_rows']}")
            print(f"   Processed at: {result['processed_at']}")
            
            # Also ensure users are in the users table
            logger.info("Ensuring users are in users table...")
            await ensure_users_in_table(csv_content)
            
            return result
        else:
            logger.error(f"❌ Import failed: {result.get('error')}")
            print(f"\n❌ Import failed: {result.get('error')}")
            return result
            
    except Exception as e:
        logger.error(f"Error importing UVM users: {e}")
        print(f"\n❌ Error: {e}")
        raise


async def ensure_users_in_table(csv_content: str):
    """Ensure all users from CSV are in the users table."""
    try:
        import io
        import json
        
        user_service = get_user_normalization_service()
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        logger.info(f"Processing {len(rows)} rows for users table...")
        
        imported_count = 0
        updated_count = 0
        
        for i, row in enumerate(rows):
            try:
                # Extract user info from CSV row
                user_info = user_service.extract_user_info_from_csv(row)
                
                # Normalize email
                email = user_info.get("email", "")
                if not email:
                    # Try to get email from row
                    email = row.get("Email", "").strip()
                    if email:
                        email = user_service.normalize_email(email)
                        user_info["email"] = email
                        user_info["user_id"] = user_service.generate_user_id(email)
                
                # Build name from First Name and Last Name
                first_name = row.get("First Name", "").strip()
                last_name = row.get("Last Name", "").strip()
                if first_name or last_name:
                    name = f"{first_name} {last_name}".strip()
                    user_info["name"] = name
                
                # Add CSV metadata
                csv_data = [{
                    "id": row.get("ID", ""),
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": row.get("Phone", ""),
                    "location": row.get("Location", ""),
                    "team": row.get("Team", ""),
                    "group": row.get("Group", ""),
                    "source": "uvm_users_csv",
                    "imported_at": datetime.now(timezone.utc).isoformat()
                }]
                
                user_info["csv_data"] = csv_data
                user_info["sources"] = ["csv", "uvm_users"]
                user_info["first_seen"] = datetime.now(timezone.utc).isoformat()
                user_info["last_seen"] = datetime.now(timezone.utc).isoformat()
                
                # Upsert user
                if await user_service.upsert_user(user_info):
                    imported_count += 1
                else:
                    updated_count += 1
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Processed {i + 1}/{len(rows)} users...")
                    
            except Exception as e:
                logger.error(f"Error processing row {i + 1}: {e}")
                continue
        
        logger.info(f"✅ Users table updated: {imported_count} new, {updated_count} updated")
        print(f"   Users table: {imported_count} new users, {updated_count} updated")
        
    except Exception as e:
        logger.error(f"Error ensuring users in table: {e}")
        print(f"   Warning: Could not update users table: {e}")


async def main():
    """Main entry point."""
    csv_file = "/Users/reif/Library/Messages/Attachments/43/03/DD7A120B-E0BE-4921-87F7-F593968D06B4/UVM Users.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    print("🚀 Starting UVM Users import...")
    print(f"   File: {csv_file}")
    
    result = await import_uvm_users(csv_file)
    
    if result and result.get("success"):
        print("\n✅ Import complete!")
        sys.exit(0)
    else:
        print("\n❌ Import failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

