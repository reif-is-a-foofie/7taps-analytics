"""
Analytics service for BigQuery operations.
"""
from typing import Dict, Any, List, Optional
import structlog
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from config.gcp_config import GCPConfig
from app.core.exceptions import ExternalServiceError, ValidationError

logger = structlog.get_logger()


class AnalyticsService:
    """Service for handling BigQuery analytics operations."""
    
    def __init__(self, gcp_config: GCPConfig):
        self.gcp_config = gcp_config
        self.bigquery_client = gcp_config.bigquery_client
    
    async def get_status(self) -> Dict[str, Any]:
        """Get BigQuery service status."""
        try:
            # Test connection by listing datasets
            datasets = list(self.bigquery_client.list_datasets())
            
            return {
                "status": "connected",
                "project_id": self.gcp_config.project_id,
                "datasets_count": len(datasets)
            }
            
        except Exception as e:
            logger.error("BigQuery status check failed", error=str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def list_datasets(self) -> List[Dict[str, Any]]:
        """List available BigQuery datasets."""
        try:
            datasets = []
            for dataset in self.bigquery_client.list_datasets():
                datasets.append({
                    "dataset_id": dataset.dataset_id,
                    "full_dataset_id": dataset.full_dataset_id,
                    "created": dataset.created.isoformat() if dataset.created else None,
                    "modified": dataset.modified.isoformat() if dataset.modified else None
                })
            
            return datasets
            
        except Exception as e:
            logger.error("Failed to list datasets", error=str(e))
            raise ExternalServiceError(f"Failed to list datasets: {str(e)}")
    
    async def list_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        """List tables in a specific dataset."""
        try:
            dataset_ref = self.bigquery_client.dataset(dataset_id)
            tables = []
            
            for table in self.bigquery_client.list_tables(dataset_ref):
                tables.append({
                    "table_id": table.table_id,
                    "full_table_id": table.full_table_id,
                    "created": table.created.isoformat() if table.created else None,
                    "modified": table.modified.isoformat() if table.modified else None
                })
            
            return tables
            
        except NotFound:
            raise ValidationError(f"Dataset '{dataset_id}' not found")
        except Exception as e:
            logger.error("Failed to list tables", error=str(e))
            raise ExternalServiceError(f"Failed to list tables: {str(e)}")
    
    async def execute_query(
        self, 
        query: str, 
        use_legacy_sql: bool = False,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a BigQuery SQL query."""
        try:
            # Configure query job
            job_config = bigquery.QueryJobConfig(
                use_legacy_sql=use_legacy_sql,
                max_results=max_results
            )
            
            # Execute query
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Convert results to list of dictionaries
            rows = []
            for row in results:
                rows.append(dict(row))
            
            return {
                "rows": rows,
                "total_rows": len(rows),
                "job_id": query_job.job_id,
                "total_bytes_processed": query_job.total_bytes_processed
            }
            
        except Exception as e:
            logger.error("Query execution failed", error=str(e))
            raise ExternalServiceError(f"Query execution failed: {str(e)}")

