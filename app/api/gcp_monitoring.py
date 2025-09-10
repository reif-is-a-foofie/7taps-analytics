"""
Google Cloud Platform Monitoring and Health Check Endpoints

This module provides monitoring endpoints for GCP infrastructure
deployment status and health checks.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from google.cloud import pubsub_v1, storage, bigquery
    from google.api_core import exceptions as google_exceptions
    from google.oauth2 import service_account
    from google.auth import default
except ImportError as e:
    logging.warning(f"Google Cloud libraries not available: {e}")

router = APIRouter(prefix="/api/debug", tags=["gcp-monitoring"])

class GCPHealthChecker:
    """Checks the health and status of GCP resources."""
    
    def __init__(self):
        self.project_id = "taps-data"
        self.credentials = self._get_credentials()
        
        # Initialize clients
        try:
            self.pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
            self.pubsub_subscriber = pubsub_v1.SubscriberClient(credentials=self.credentials)
            self.storage_client = storage.Client(credentials=self.credentials)
            self.bq_client = bigquery.Client(credentials=self.credentials)
        except Exception as e:
            logging.error(f"Failed to initialize GCP clients: {e}")
            self.pubsub_publisher = None
            self.pubsub_subscriber = None
            self.storage_client = None
            self.bq_client = None

    def _get_credentials(self):
        """Get Google Cloud credentials."""
        key_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'google-cloud-key.json'
        )

        if os.path.exists(key_file):
            return service_account.Credentials.from_service_account_file(key_file)
        else:
            # Try to use default credentials
            try:
                credentials, _ = default()
                return credentials
            except Exception:
                return None

    def check_pubsub_health(self) -> Dict[str, Any]:
        """Check Pub/Sub topics and subscriptions health."""
        if not self.pubsub_publisher or not self.pubsub_subscriber:
            return {"status": "error", "message": "Pub/Sub clients not initialized"}
        
        try:
            # Check topics
            topics = list(self.pubsub_publisher.list_topics(
                request={"project": f"projects/{self.project_id}"}
            ))
            
            topic_names = [t.name.split('/')[-1] for t in topics]
            expected_topics = ["xapi-ingestion-topic"]
            
            # Check subscriptions
            subscriptions = list(self.pubsub_subscriber.list_subscriptions(
                request={"project": f"projects/{self.project_id}"}
            ))
            
            subscription_names = [s.name.split('/')[-1] for s in subscriptions]
            expected_subscriptions = ["xapi-storage-subscriber", "xapi-bigquery-subscriber"]
            
            return {
                "status": "healthy",
                "topics": {
                    "found": topic_names,
                    "expected": expected_topics,
                    "missing": [t for t in expected_topics if t not in topic_names]
                },
                "subscriptions": {
                    "found": subscription_names,
                    "expected": expected_subscriptions,
                    "missing": [s for s in expected_subscriptions if s not in subscription_names]
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_storage_health(self) -> Dict[str, Any]:
        """Check Cloud Storage buckets health."""
        if not self.storage_client:
            return {"status": "error", "message": "Storage client not initialized"}
        
        try:
            buckets = list(self.storage_client.list_buckets())
            bucket_names = [b.name for b in buckets]
            expected_buckets = ["taps-data-raw-xapi"]
            
            return {
                "status": "healthy" if all(b in bucket_names for b in expected_buckets) else "partial",
                "buckets": {
                    "found": bucket_names,
                    "expected": expected_buckets,
                    "missing": [b for b in expected_buckets if b not in bucket_names]
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def check_bigquery_health(self) -> Dict[str, Any]:
        """Check BigQuery datasets and tables health."""
        if not self.bq_client:
            return {"status": "error", "message": "BigQuery client not initialized"}
        
        try:
            # Check datasets
            datasets = list(self.bq_client.list_datasets())
            dataset_names = [d.dataset_id for d in datasets]
            expected_datasets = ["taps_data"]
            
            # Check tables in the main dataset
            tables = []
            if "taps_data" in dataset_names:
                dataset_ref = self.bq_client.dataset("taps_data")
                tables = list(self.bq_client.list_tables(dataset_ref))
            
            table_names = [t.table_id for t in tables]
            expected_tables = ["users", "lessons", "questions", "user_responses", "user_activities", "xapi_events"]
            
            return {
                "status": "healthy" if all(d in dataset_names for d in expected_datasets) else "partial",
                "datasets": {
                    "found": dataset_names,
                    "expected": expected_datasets,
                    "missing": [d for d in expected_datasets if d not in dataset_names]
                },
                "tables": {
                    "found": table_names,
                    "expected": expected_tables,
                    "missing": [t for t in expected_tables if t not in table_names]
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall GCP infrastructure health."""
        pubsub_health = self.check_pubsub_health()
        storage_health = self.check_storage_health()
        bigquery_health = self.check_bigquery_health()
        
        # Determine overall status
        statuses = [pubsub_health.get("status"), storage_health.get("status"), bigquery_health.get("status")]
        
        if all(s == "healthy" for s in statuses):
            overall_status = "healthy"
        elif any(s == "error" for s in statuses):
            overall_status = "error"
        else:
            overall_status = "partial"
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "project_id": self.project_id,
            "components": {
                "pubsub": pubsub_health,
                "storage": storage_health,
                "bigquery": bigquery_health
            }
        }

# Initialize health checker
health_checker = GCPHealthChecker()

@router.get("/gcp-infrastructure-status")
async def get_gcp_infrastructure_status():
    """
    Get the current status of GCP infrastructure deployment.
    
    Returns:
        JSON response with infrastructure status
    """
    try:
        status = health_checker.get_overall_health()
        return JSONResponse(content=status)
    except Exception as e:
        logging.error(f"Failed to get GCP infrastructure status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gcp-resource-health")
async def get_gcp_resource_health():
    """
    Get detailed health information for each GCP resource type.
    
    Returns:
        JSON response with detailed health information
    """
    try:
        health_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pubsub": health_checker.check_pubsub_health(),
            "storage": health_checker.check_storage_health(),
            "bigquery": health_checker.check_bigquery_health()
        }
        return JSONResponse(content=health_info)
    except Exception as e:
        logging.error(f"Failed to get GCP resource health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-gcp-deployment")
async def validate_gcp_deployment():
    """
    Validate the complete GCP deployment and return validation results.
    
    Returns:
        JSON response with validation results
    """
    try:
        validation_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validation_passed": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check each component
        pubsub_health = health_checker.check_pubsub_health()
        storage_health = health_checker.check_storage_health()
        bigquery_health = health_checker.check_bigquery_health()
        
        # Collect issues
        if pubsub_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("Pub/Sub service is not accessible")
        
        if storage_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("Cloud Storage service is not accessible")
        elif storage_health.get("status") == "partial":
            validation_results["recommendations"].append("Some Cloud Storage buckets are missing - check billing account")
        
        if bigquery_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("BigQuery service is not accessible")
        elif bigquery_health.get("status") == "partial":
            validation_results["recommendations"].append("Some BigQuery tables are missing")
        
        # Add component details
        validation_results["components"] = {
            "pubsub": pubsub_health,
            "storage": storage_health,
            "bigquery": bigquery_health
        }
        
        return JSONResponse(content=validation_results)
    except Exception as e:
        logging.error(f"Failed to validate GCP deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gcp-deployment-summary")
async def get_gcp_deployment_summary():
    """
    Get a summary of the GCP deployment status.
    
    Returns:
        JSON response with deployment summary
    """
    try:
        health = health_checker.get_overall_health()
        
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": health["project_id"],
            "overall_status": health["overall_status"],
            "deployment_complete": health["overall_status"] in ["healthy", "partial"],
            "components_status": {
                "pubsub": health["components"]["pubsub"]["status"],
                "storage": health["components"]["storage"]["status"],
                "bigquery": health["components"]["bigquery"]["status"]
            },
            "next_steps": []
        }
        
        # Add next steps based on status
        if health["overall_status"] == "error":
            summary["next_steps"].append("Check GCP credentials and project permissions")
        elif health["overall_status"] == "partial":
            summary["next_steps"].append("Complete missing resource creation")
            if health["components"]["storage"]["status"] != "healthy":
                summary["next_steps"].append("Enable billing account for Cloud Storage")
        else:
            summary["next_steps"].append("Deploy Cloud Function for xAPI ingestion")
            summary["next_steps"].append("Test end-to-end data flow")
        
        return JSONResponse(content=summary)
    except Exception as e:
        logging.error(f"Failed to get GCP deployment summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
