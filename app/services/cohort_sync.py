"""
Cohort Sync Service

Automatically syncs data-derived cohorts from users table to cohorts table.
Runs on CSV import and can be triggered manually.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
from app.logging_config import get_logger
from app.config.gcp_config import get_gcp_config

logger = get_logger("cohort_sync")


class CohortSyncService:
    """Service for syncing data-derived cohorts to the cohorts table."""
    
    def __init__(self):
        self.gcp_config = get_gcp_config()
        self.bigquery_client = self.gcp_config.bigquery_client
        self.dataset_id = self.gcp_config.bigquery_dataset
    
    async def sync_cohorts_from_users(self) -> Dict[str, Any]:
        """
        Sync cohorts from users table to cohorts table.
        Discovers all Team+Group combinations and creates/updates cohort records.
        """
        try:
            # Get all unique Team+Group combinations from users
            query = f"""
            SELECT 
                csv_data[OFFSET(0)].team as team,
                csv_data[OFFSET(0)].group as group_name,
                COUNT(*) as user_count
            FROM `{self.dataset_id}.users`
            WHERE csv_data IS NOT NULL 
                AND ARRAY_LENGTH(csv_data) > 0
                AND csv_data[OFFSET(0)].team IS NOT NULL
                AND csv_data[OFFSET(0)].group IS NOT NULL
            GROUP BY team, group_name
            """
            
            results = list(self.bigquery_client.query(query).result())
            
            cohorts_to_sync = []
            for row in results:
                team = row.team or "X"
                group = row.group_name or "X"
                cohort_name = f"{group} {team}".strip()
                cohort_id = cohort_name.lower().replace(" ", "_").replace("-", "_")
                
                cohorts_to_sync.append({
                    "cohort_id": cohort_id,
                    "cohort_name": cohort_name,
                    "team": team,
                    "group_name": group,
                    "user_count": row.user_count,
                    "source": "data_derived"
                })
            
            # Get statement counts for each cohort
            for cohort in cohorts_to_sync:
                statement_count = await self._get_statement_count_for_cohort(cohort["cohort_id"])
                cohort["statement_count"] = statement_count
            
            # Upsert cohorts into cohorts table
            synced_count = await self._upsert_cohorts(cohorts_to_sync)
            
            logger.info(f"Synced {synced_count} data-derived cohorts to database")
            
            return {
                "success": True,
                "synced_count": synced_count,
                "cohorts": cohorts_to_sync
            }
            
        except Exception as e:
            logger.error(f"Error syncing cohorts: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_statement_count_for_cohort(self, cohort_id: str) -> int:
        """Get statement count for a cohort from statements table."""
        try:
            from google.cloud import bigquery
            
            # Use the cohort_id from CSV metadata in statements
            query = f"""
            SELECT COUNT(*) as count
            FROM `{self.dataset_id}.statements`
            WHERE JSON_EXTRACT_SCALAR(raw_json, '$.context.extensions."https://7taps.com/csv-metadata".cohort_id') = @cohort_id
            """
            
            job_config = bigquery.QueryJobConfig()
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter("cohort_id", "STRING", cohort_id)
            ]
            
            results = list(self.bigquery_client.query(query, job_config=job_config).result())
            if results:
                return results[0].count
            return 0
            
        except Exception as e:
            logger.warning(f"Error getting statement count for cohort {cohort_id}: {e}")
            return 0
    
    async def _upsert_cohorts(self, cohorts: List[Dict[str, Any]]) -> int:
        """Upsert cohorts into the cohorts table."""
        try:
            from google.cloud import bigquery
            
            table_id = f"{self.dataset_id}.cohorts"
            
            # Insert each cohort individually using MERGE
            synced = 0
            for cohort in cohorts:
                merge_query = f"""
                MERGE `{table_id}` T
                USING (SELECT 
                    @cohort_id as cohort_id,
                    @cohort_name as cohort_name,
                    @team as team,
                    @group_name as group_name,
                    CONCAT('Data-derived cohort: ', @cohort_name) as description,
                    @source as source,
                    @user_count as user_count,
                    @statement_count as statement_count,
                    CURRENT_TIMESTAMP() as created_at,
                    CURRENT_TIMESTAMP() as updated_at,
                    TRUE as active
                ) S
                ON T.cohort_id = S.cohort_id AND T.source = 'data_derived'
                WHEN MATCHED THEN
                  UPDATE SET
                    cohort_name = S.cohort_name,
                    team = S.team,
                    group_name = S.group_name,
                    user_count = S.user_count,
                    statement_count = S.statement_count,
                    updated_at = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN
                  INSERT (cohort_id, cohort_name, team, group_name, description, source, user_count, statement_count, created_at, updated_at, active)
                  VALUES (S.cohort_id, S.cohort_name, S.team, S.group_name, S.description, S.source, S.user_count, S.statement_count, S.created_at, S.updated_at, S.active)
                """
                
                job_config = bigquery.QueryJobConfig()
                job_config.query_parameters = [
                    bigquery.ScalarQueryParameter("cohort_id", "STRING", cohort["cohort_id"]),
                    bigquery.ScalarQueryParameter("cohort_name", "STRING", cohort["cohort_name"]),
                    bigquery.ScalarQueryParameter("team", "STRING", cohort["team"]),
                    bigquery.ScalarQueryParameter("group_name", "STRING", cohort["group_name"]),
                    bigquery.ScalarQueryParameter("source", "STRING", cohort["source"]),
                    bigquery.ScalarQueryParameter("user_count", "INT64", cohort["user_count"]),
                    bigquery.ScalarQueryParameter("statement_count", "INT64", cohort["statement_count"])
                ]
                
                self.bigquery_client.query(merge_query, job_config=job_config).result()
                synced += 1
            
            return synced
            
        except Exception as e:
            logger.error(f"Error upserting cohorts: {e}")
            raise


# Global service instance
_cohort_sync_service = None

def get_cohort_sync_service() -> CohortSyncService:
    """Get the global cohort sync service instance."""
    global _cohort_sync_service
    if _cohort_sync_service is None:
        _cohort_sync_service = CohortSyncService()
    return _cohort_sync_service

