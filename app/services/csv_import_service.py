"""
CSV Import Service with User Normalization

Handles CSV file uploads and normalizes user data across sources.
"""

import csv
import io
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.logging_config import get_logger
from app.services.user_normalization import get_user_normalization_service
from app.services.cohort_sync import get_cohort_sync_service
from app.config.gcp_config import get_gcp_config

logger = get_logger("csv_import_service")


class CSVImportService:
    """Service for importing CSV data with user normalization."""
    
    def __init__(self):
        self.gcp_config = get_gcp_config()
        self.bigquery_client = self.gcp_config.bigquery_client
        self.dataset_id = self.gcp_config.bigquery_dataset
    
    async def import_csv_data(self, csv_content: str, filename: str) -> Dict[str, Any]:
        """Import CSV data with user normalization."""
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            
            if not rows:
                return {
                    "success": False,
                    "error": "No data found in CSV file",
                    "imported_count": 0
                }
            
            logger.info(f"Importing {len(rows)} rows from {filename}")
            
            # Process each row with user normalization
            processed_rows = []
            errors = []
            for i, row in enumerate(rows):
                try:
                    # Normalize user data
                    user_service = get_user_normalization_service()
                    normalized_row = await user_service.normalize_csv_row(row)
                    if normalized_row:
                        processed_rows.append(normalized_row)
                    else:
                        errors.append(f"Row {i + 1}: normalize_csv_row returned None")
                    
                    if (i + 1) % 100 == 0:
                        logger.info(f"Processed {i + 1}/{len(rows)} rows")
                        
                except Exception as e:
                    error_msg = f"Error processing row {i + 1}: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    continue
            
            if errors:
                logger.warning(f"Encountered {len(errors)} errors during processing. First few: {errors[:5]}")
            
            # Store processed data in BigQuery
            await self._store_csv_data(processed_rows, filename)
            
            # Sync cohorts after CSV import
            try:
                cohort_sync_service = get_cohort_sync_service()
                sync_result = await cohort_sync_service.sync_cohorts_from_users()
                logger.info(f"Cohort sync after CSV import: {sync_result.get('synced_count', 0)} cohorts synced")
            except Exception as e:
                logger.warning(f"Failed to sync cohorts after CSV import: {e}")
            
            return {
                "success": True,
                "imported_count": len(processed_rows),
                "total_rows": len(rows),
                "filename": filename,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error importing CSV data: {e}")
            return {
                "success": False,
                "error": str(e),
                "imported_count": 0
            }
    
    async def _store_csv_data(self, rows: List[Dict[str, Any]], filename: str) -> bool:
        """Store processed CSV data in BigQuery."""
        try:
            table_id = f"{self.dataset_id}.csv_imports"
            
            # Prepare data for BigQuery
            bigquery_rows = []
            for row in rows:
                bigquery_row = {
                    "filename": filename,
                    "normalized_user_id": row.get("normalized_user_id", ""),
                    "original_data": json.dumps(row),
                    "imported_at": datetime.now(timezone.utc).isoformat()
                }
                bigquery_rows.append(bigquery_row)
            
            # Insert into BigQuery
            table = self.bigquery_client.get_table(table_id)
            errors = self.bigquery_client.insert_rows_json(table, bigquery_rows)
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
                return False
            
            logger.info(f"Successfully stored {len(bigquery_rows)} rows in BigQuery")
            return True
            
        except Exception as e:
            logger.error(f"Error storing CSV data in BigQuery: {e}")
            return False
    
    async def get_user_merge_report(self) -> Dict[str, Any]:
        """Generate a report of user merging across data sources."""
        try:
            query = f"""
            WITH user_sources AS (
                SELECT 
                    normalized_user_id,
                    email,
                    name,
                    sources,
                    COUNT(*) as total_activities,
                    MIN(first_seen) as first_seen,
                    MAX(last_seen) as last_seen
                FROM `{self.dataset_id}.users`
                GROUP BY normalized_user_id, email, name, sources
            ),
            duplicate_emails AS (
                SELECT 
                    email,
                    COUNT(*) as user_count,
                    STRING_AGG(normalized_user_id, ', ') as user_ids,
                    STRING_AGG(name, ' | ') as names
                FROM user_sources
                WHERE email IS NOT NULL AND email != ''
                GROUP BY email
                HAVING COUNT(*) > 1
            ),
            source_breakdown AS (
                SELECT 
                    source,
                    COUNT(*) as user_count
                FROM `{self.dataset_id}.users`, UNNEST(sources) as source
                GROUP BY source
            )
            SELECT 
                (SELECT COUNT(*) FROM user_sources) as total_users,
                (SELECT COUNT(*) FROM duplicate_emails) as duplicate_email_count,
                (SELECT SUM(user_count) FROM duplicate_emails) as users_with_duplicates,
                (SELECT COUNT(*) FROM source_breakdown) as data_sources
            """
            
            results = self.bigquery_client.query(query)
            stats = list(results)[0] if results else {}
            
            # Get sample duplicates
            duplicate_query = f"""
            SELECT 
                email,
                user_count,
                user_ids,
                names
            FROM (
                SELECT 
                    email,
                    COUNT(*) as user_count,
                    STRING_AGG(normalized_user_id, ', ') as user_ids,
                    STRING_AGG(name, ' | ') as names
                FROM `{self.dataset_id}.users`
                WHERE email IS NOT NULL AND email != ''
                GROUP BY email
                HAVING COUNT(*) > 1
            )
            ORDER BY user_count DESC
            LIMIT 10
            """
            
            duplicate_results = self.bigquery_client.query(duplicate_query)
            sample_duplicates = [dict(row) for row in duplicate_results]
            
            return {
                "success": True,
                "stats": stats,
                "sample_duplicates": sample_duplicates,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating user merge report: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global instance
csv_import_service = CSVImportService()
