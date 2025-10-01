"""
Migration API for database schema updates.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.config.gcp_config import get_gcp_config
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("migration")

@router.post("/migration/add-normalized-user-id")
async def add_normalized_user_id_column() -> Dict[str, Any]:
    """Add the normalized_user_id column to the statements table."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        
        # Add the normalized_user_id column
        query = """
        ALTER TABLE `taps-data.taps_data.statements`
        ADD COLUMN IF NOT EXISTS normalized_user_id STRING OPTIONS(description="Normalized user ID (SHA256 hash of normalized email) for consistent user tracking across sources")
        """
        
        job = client.query(query)
        job.result()  # Wait for the job to complete
        
        logger.info("Successfully added normalized_user_id column to statements table")
        
        return {
            "success": True,
            "message": "Successfully added normalized_user_id column to statements table"
        }
        
    except Exception as e:
        logger.error(f"Failed to add normalized_user_id column: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.post("/migration/create-users-table")
async def create_users_table() -> Dict[str, Any]:
    """Create the users table for normalized user profiles."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        
        # Create the users table
        query = """
        CREATE TABLE IF NOT EXISTS `taps-data.taps_data.users` (
            user_id STRING NOT NULL OPTIONS(description="Normalized and consistent user ID (SHA256 hash of normalized email)"),
            email STRING NOT NULL OPTIONS(description="Normalized email address (lowercase, trimmed)"),
            name STRING OPTIONS(description="User's display name"),
            sources ARRAY<STRING> OPTIONS(description="List of data sources for this user (e.g., 'xapi', 'csv')"),
            first_seen TIMESTAMP OPTIONS(description="Timestamp when the user was first seen"),
            last_seen TIMESTAMP OPTIONS(description="Timestamp when the user was last active"),
            activity_count INT64 OPTIONS(description="Total number of activities recorded for this user"),
            xapi_actor_ids ARRAY<STRING> OPTIONS(description="List of original xAPI actor IDs associated with this user"),
            csv_data ARRAY<JSON> OPTIONS(description="Array of raw CSV data rows associated with this user")
        )
        PARTITION BY DATE(first_seen)
        CLUSTER BY user_id
        OPTIONS(
            description="Normalized user profiles, merging data from various sources like xAPI and CSV uploads."
        )
        """
        
        job = client.query(query)
        job.result()  # Wait for the job to complete
        
        logger.info("Successfully created users table")
        
        return {
            "success": True,
            "message": "Successfully created users table"
        }
        
    except Exception as e:
        logger.error(f"Failed to create users table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.post("/migration/create-csv-imports-table")
async def create_csv_imports_table() -> Dict[str, Any]:
    """Create the csv_imports table for CSV import logging."""
    try:
        gcp_config = get_gcp_config()
        client = gcp_config.bigquery_client
        
        # Create the csv_imports table
        query = """
        CREATE TABLE IF NOT EXISTS `taps-data.taps_data.csv_imports` (
            import_timestamp TIMESTAMP NOT NULL OPTIONS(description="Timestamp of the CSV import"),
            filename STRING NOT NULL OPTIONS(description="Original filename of the imported CSV"),
            row_number INT64 NOT NULL OPTIONS(description="Row number in the original CSV file"),
            original_data JSON OPTIONS(description="Raw JSON representation of the imported CSV row"),
            normalized_user_id STRING OPTIONS(description="Normalized user ID linked to this CSV row"),
            normalized_email STRING OPTIONS(description="Normalized email from the CSV row")
        )
        PARTITION BY DATE(import_timestamp)
        CLUSTER BY normalized_user_id
        OPTIONS(
            description="Log of CSV data imports, linked to normalized user profiles."
        )
        """
        
        job = client.query(query)
        job.result()  # Wait for the job to complete
        
        logger.info("Successfully created csv_imports table")
        
        return {
            "success": True,
            "message": "Successfully created csv_imports table"
        }
        
    except Exception as e:
        logger.error(f"Failed to create csv_imports table: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

