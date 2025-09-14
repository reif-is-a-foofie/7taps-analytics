"""
Google Cloud Platform configuration and client initialization.
"""
from typing import Optional
import json
import os
from google.cloud import pubsub_v1, storage, bigquery
from google.auth import default
from google.oauth2 import service_account
import logging

logger = logging.getLogger(__name__)


class GCPConfig:
    """Centralized GCP configuration and client management."""
    
    def __init__(self, project_id: str, service_account_key: Optional[str] = None):
        self.project_id = project_id
        self.service_account_key = service_account_key
        self._credentials = None
        self._clients = {}
    
    @property
    def credentials(self):
        """Get or create GCP credentials."""
        if not self._credentials:
            if self.service_account_key:
                try:
                    key_data = json.loads(self.service_account_key)
                    self._credentials = service_account.Credentials.from_service_account_info(key_data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid service account key: {e}")
                    raise
            else:
                self._credentials, _ = default()
        return self._credentials
    
    @property
    def pubsub_client(self) -> pubsub_v1.PublisherClient:
        """Get Pub/Sub publisher client."""
        if 'pubsub' not in self._clients:
            self._clients['pubsub'] = pubsub_v1.PublisherClient(
                credentials=self.credentials
            )
        return self._clients['pubsub']
    
    @property
    def storage_client(self) -> storage.Client:
        """Get Cloud Storage client."""
        if 'storage' not in self._clients:
            self._clients['storage'] = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
        return self._clients['storage']
    
    @property
    def bigquery_client(self) -> bigquery.Client:
        """Get BigQuery client."""
        if 'bigquery' not in self._clients:
            self._clients['bigquery'] = bigquery.Client(
                project=self.project_id,
                credentials=self.credentials
            )
        return self._clients['bigquery']
    
    def get_topic_path(self, topic_name: str) -> str:
        """Get full topic path."""
        return f"projects/{self.project_id}/topics/{topic_name}"
    
    def get_subscription_path(self, subscription_name: str) -> str:
        """Get full subscription path."""
        return f"projects/{self.project_id}/subscriptions/{subscription_name}"
    
    def get_bucket_path(self, bucket_name: str) -> str:
        """Get bucket path."""
        return f"gs://{bucket_name}"
    
    def validate_connection(self) -> dict:
        """Validate GCP connections and return status."""
        status = {
            "project_id": self.project_id,
            "credentials": "valid" if self.credentials else "invalid",
            "services": {}
        }
        
        # Test Pub/Sub
        try:
            self.pubsub_client.list_topics(project=f"projects/{self.project_id}")
            status["services"]["pubsub"] = "connected"
        except Exception as e:
            status["services"]["pubsub"] = f"error: {str(e)}"
        
        # Test Storage
        try:
            self.storage_client.list_buckets()
            status["services"]["storage"] = "connected"
        except Exception as e:
            status["services"]["storage"] = f"error: {str(e)}"
        
        # Test BigQuery
        try:
            self.bigquery_client.list_datasets()
            status["services"]["bigquery"] = "connected"
        except Exception as e:
            status["services"]["bigquery"] = f"error: {str(e)}"
        
        return status


# Global GCP config instance
gcp_config = GCPConfig(
    project_id=os.getenv("GCP_PROJECT_ID", "taps-data"),
    service_account_key=os.getenv("GOOGLE_CLOUD_KEY")
)

