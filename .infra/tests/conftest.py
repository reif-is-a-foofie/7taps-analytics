"""Pytest configuration and fixtures for 7taps Analytics tests."""

import pytest
from unittest.mock import Mock, patch
import os

# Mock GCP credentials before any imports
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/dev/null"

@pytest.fixture(autouse=True)
def mock_gcp_services():
    """Mock GCP services to avoid credential requirements."""
    with patch('app.config.gcp_config.get_gcp_config') as mock_config:
        # Create mock GCP config
        mock_gcp_config = Mock()
        mock_gcp_config.project_id = "test-project"
        mock_gcp_config.bigquery_dataset = "test_dataset"
        mock_gcp_config.pubsub_topic = "test-topic"
        mock_gcp_config.storage_bucket = "test-bucket"
        mock_gcp_config.credentials = Mock()
        mock_gcp_config.bigquery_client = Mock()
        mock_gcp_config.pubsub_client = Mock()
        mock_gcp_config.storage_client = Mock()
        
        mock_config.return_value = mock_gcp_config
        
        yield mock_gcp_config

@pytest.fixture(autouse=True)
def mock_user_normalization_service():
    """Mock user normalization service to avoid GCP dependencies."""
    with patch('app.services.user_normalization.get_user_normalization_service') as mock_service:
        mock_service_instance = Mock()
        mock_service_instance.normalize_xapi_statement.return_value = {"normalized_user_id": "test-user"}
        mock_service_instance.normalize_csv_row.return_value = {"normalized_user_id": "test-user"}
        mock_service.return_value = mock_service_instance
        
        yield mock_service_instance
