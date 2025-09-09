"""
Google Cloud Platform configuration for xAPI ingestion service.
Handles authentication, Pub/Sub client setup, and Cloud Function configuration.
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from google.auth import default
from google.oauth2 import service_account
from google.cloud import pubsub_v1
from google.api_core import exceptions


class GCPConfig:
    """Configuration class for Google Cloud Platform services."""

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID", "taps-data")
        self.service_account_key_path = os.getenv("GCP_SERVICE_ACCOUNT_KEY_PATH", "google-cloud-key.json")
        self.pubsub_topic = os.getenv("GCP_PUBSUB_TOPIC", "xapi-ingestion-topic")
        self.location = os.getenv("GCP_LOCATION", "us-central1")

        self._credentials = None
        self._pubsub_publisher = None

    @property
    def credentials(self):
        """Get Google Cloud credentials."""
        if self._credentials is None:
            try:
                # Try to use service account key file first
                if os.path.exists(self.service_account_key_path):
                    self._credentials = service_account.Credentials.from_service_account_file(
                        self.service_account_key_path,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                else:
                    # Fall back to default credentials (for Cloud Functions)
                    self._credentials, _ = default()
            except Exception as e:
                raise ValueError(f"Failed to load GCP credentials: {str(e)}")

        return self._credentials

    @property
    def pubsub_publisher(self) -> pubsub_v1.PublisherClient:
        """Get Pub/Sub publisher client."""
        if self._pubsub_publisher is None:
            self._pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
        return self._pubsub_publisher

    def get_topic_path(self) -> str:
        """Get the full Pub/Sub topic path."""
        return self.pubsub_publisher.topic_path(self.project_id, self.pubsub_topic)

    def validate_config(self) -> Dict[str, Any]:
        """Validate GCP configuration and return status."""
        status = {
            "project_id": self.project_id,
            "pubsub_topic": self.pubsub_topic,
            "location": self.location,
            "service_account_loaded": False,
            "pubsub_topic_exists": False,
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

        except Exception as e:
            status["errors"].append(f"Configuration validation error: {str(e)}")

        return status


# Global configuration instance
gcp_config = GCPConfig()
