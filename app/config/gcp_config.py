"""
Google Cloud Platform configuration for xAPI ingestion service.
Handles authentication, Pub/Sub client setup, and Cloud Function configuration.
"""

import os
import json
from typing import Optional, Dict, Any
from google.auth import default
from google.cloud import pubsub_v1, storage, bigquery
from google.api_core import exceptions
import importlib.util


def _load_settings_module():
    """Load app.config.settings without triggering circular imports."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.py")
    spec = importlib.util.spec_from_file_location("config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


settings = _load_settings_module().settings


class GCPConfig:
    """Configuration class for Google Cloud Platform services."""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT", settings.GCP_PROJECT_ID)
        self.service_account_key_path = os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            settings.GCP_SERVICE_ACCOUNT_KEY_PATH or "",
        )
        self.pubsub_topic = settings.GCP_PUBSUB_TOPIC
        self.storage_bucket = settings.GCP_STORAGE_BUCKET
        self.bigquery_dataset = settings.GCP_BIGQUERY_DATASET
        self.location = settings.GCP_LOCATION

        self._credentials = None
        self._pubsub_publisher = None
        self._storage_client = None
        self._bigquery_client = None

    @property
    def credentials(self):
        """Get Google Cloud credentials."""
        if self._credentials is None:
            try:
                # Check if we're in Cloud Run environment
                if os.getenv("K_SERVICE") or os.getenv("DEPLOYMENT_MODE") == "cloud_run":
                    # In Cloud Run, use default credentials (metadata service)
                    self._credentials, _ = default()
                else:
                    # For local development, try service account key file
                    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    if key_path and os.path.exists(key_path):
                        self._credentials, _ = default()
                    else:
                        # Fallback to default credentials
                        self._credentials, _ = default()
            except Exception as e:
                # Return None instead of raising error to allow graceful degradation
                print(f"Warning: Failed to load GCP credentials: {str(e)}")
                self._credentials = None

        return self._credentials

    @property
    def pubsub_publisher(self) -> pubsub_v1.PublisherClient:
        """Get Pub/Sub publisher client."""
        if self._pubsub_publisher is None:
            if self.credentials:
                self._pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
            else:
                raise ValueError("GCP credentials not available for Pub/Sub")
        return self._pubsub_publisher

    @property
    def storage_client(self) -> storage.Client:
        """Get Cloud Storage client."""
        if self._storage_client is None:
            if self.credentials:
                self._storage_client = storage.Client(credentials=self.credentials, project=self.project_id)
            else:
                raise ValueError("GCP credentials not available for Cloud Storage")
        return self._storage_client

    @property
    def bigquery_client(self) -> bigquery.Client:
        """Get BigQuery client."""
        if self._bigquery_client is None:
            if self.credentials:
                self._bigquery_client = bigquery.Client(credentials=self.credentials, project=self.project_id)
            else:
                raise ValueError("GCP credentials not available for BigQuery")
        return self._bigquery_client

    def get_topic_path(self) -> str:
        """Get the full Pub/Sub topic path."""
        return self.pubsub_publisher.topic_path(self.project_id, self.pubsub_topic)

    def validate_config(self) -> Dict[str, Any]:
        """Validate GCP configuration and return status."""
        status = {
            "project_id": self.project_id,
            "pubsub_topic": self.pubsub_topic,
            "storage_bucket": self.storage_bucket,
            "bigquery_dataset": self.bigquery_dataset,
            "location": self.location,
            "service_account_loaded": False,
            "pubsub_topic_exists": False,
            "storage_bucket_exists": False,
            "bigquery_dataset_exists": False,
            "credentials_valid": False,
            "errors": []
        }

        try:
            # Test credentials
            if self.credentials:
                status["credentials_valid"] = True

            # Check if service account key was loaded
            if os.path.exists(self.service_account_key_path):
                status["service_account_loaded"] = True

            # Test Pub/Sub topic access
            try:
                topic_path = self.get_topic_path()
                # This will raise an exception if topic doesn't exist or we don't have access
                self.pubsub_publisher.get_topic(request={"topic": topic_path})
                status["pubsub_topic_exists"] = True
            except exceptions.NotFound:
                status["errors"].append(f"Pub/Sub topic '{self.pubsub_topic}' does not exist")
            except Exception as e:
                status["errors"].append(f"Pub/Sub access error: {str(e)}")

            # Test Cloud Storage bucket access
            try:
                bucket = self.storage_client.bucket(self.storage_bucket)
                if bucket.exists():
                    status["storage_bucket_exists"] = True
                else:
                    status["errors"].append(f"Cloud Storage bucket '{self.storage_bucket}' does not exist")
            except Exception as e:
                status["errors"].append(f"Cloud Storage access error: {str(e)}")

            # Test BigQuery dataset access
            try:
                dataset_ref = self.bigquery_client.dataset(self.bigquery_dataset)
                dataset = self.bigquery_client.get_dataset(dataset_ref)
                status["bigquery_dataset_exists"] = True
            except exceptions.NotFound:
                status["errors"].append(f"BigQuery dataset '{self.bigquery_dataset}' does not exist")
            except Exception as e:
                status["errors"].append(f"BigQuery access error: {str(e)}")

        except Exception as e:
            status["errors"].append(f"Configuration validation error: {str(e)}")

        return status


# Global configuration instance (lazy-loaded)
_gcp_config = None

def get_gcp_config() -> GCPConfig:
    """Get the global GCP config instance (lazy-loaded)."""
    global _gcp_config
    if _gcp_config is None:
        _gcp_config = GCPConfig()
    return _gcp_config

# For backward compatibility: export an instantiated config
gcp_config = get_gcp_config()
