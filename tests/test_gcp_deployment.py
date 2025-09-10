"""
Test Google Cloud Platform Deployment (gc06)

Tests for the complete Google Cloud Platform deployment functionality.
"""

import os
import sys
import json
import pytest
import tempfile
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# Test client for API tests
client = TestClient(app)

class TestGCPDeploymentConfig:
    """Test GCP deployment configuration file."""

    def test_config_file_exists(self):
        """Test that the GCP deployment configuration file exists."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'gcp_deployment_config.json'
        )
        assert os.path.exists(config_path), "GCP deployment config file should exist"

    def test_config_file_valid_json(self):
        """Test that the configuration file contains valid JSON."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'gcp_deployment_config.json'
        )

        with open(config_path, 'r') as f:
            config = json.load(f)

        # Test required top-level keys
        required_keys = [
            'gcp_project', 'enabled_apis', 'service_account',
            'cloud_functions', 'pubsub', 'cloud_storage', 'bigquery'
        ]

        for key in required_keys:
            assert key in config, f"Configuration should contain '{key}' key"

class TestGCPMonitoringEndpoints:
    """Test GCP monitoring and health check endpoints."""

    @patch('app.api.legacy_heroku_endpoints.gcp_config')
    def test_gcp_infrastructure_status_endpoint(self, mock_gcp_config):
        """Test GCP infrastructure status endpoint."""
        mock_gcp_config.project_id = 'test-project'
        mock_gcp_config.pubsub_topic = 'test-topic'
        mock_gcp_config.pubsub_storage_subscription = 'test-storage-sub'
        mock_gcp_config.pubsub_bigquery_subscription = 'test-bq-sub'
        mock_gcp_config.storage_bucket = 'test-bucket'
        mock_gcp_config.bigquery_dataset = 'test-dataset'

        response = client.get("/api/debug/gcp-infrastructure-status")

        assert response.status_code in [200, 206]
        data = response.json()

        assert 'timestamp' in data
        assert 'gcp_project' in data
        assert 'components' in data
        assert 'overall_status' in data

    @patch('app.api.legacy_heroku_endpoints.MigrationValidator')
    @patch('app.api.legacy_heroku_endpoints.gcp_config')
    def test_validate_gcp_deployment_endpoint(self, mock_gcp_config, mock_validator):
        """Test GCP deployment validation endpoint."""
        mock_gcp_config.project_id = 'test-project'

        mock_instance = Mock()
        mock_instance.run_full_validation.return_value = {
            'migration_complete': True,
            'summary': {'total_validations': 5, 'passed': 5, 'failed': 0},
            'errors': []
        }
        mock_validator.return_value = mock_instance

        response = client.post("/api/debug/validate-gcp-deployment")

        assert response.status_code in [200, 206]
        data = response.json()

        assert 'validation_timestamp' in data
        assert 'gcp_project' in data
        assert 'deployment_status' in data
        assert 'recommendations' in data

    @patch('app.api.legacy_heroku_endpoints.gcp_config')
    def test_gcp_resource_health_endpoint(self, mock_gcp_config):
        """Test GCP resource health endpoint."""
        mock_gcp_config.project_id = 'test-project'
        mock_gcp_config.pubsub_storage_subscription = 'test-storage-sub'
        mock_gcp_config.pubsub_bigquery_subscription = 'test-bq-sub'
        mock_gcp_config.storage_bucket = 'test-bucket'
        mock_gcp_config.bigquery_dataset = 'test-dataset'

        response = client.get("/api/debug/gcp-resource-health")

        assert response.status_code in [200, 206, 503]
        data = response.json()

        assert 'timestamp' in data
        assert 'gcp_project' in data
        assert 'resources' in data
        assert 'overall_health' in data

class TestGCPDeploymentScripts:
    """Test GCP deployment scripts exist and are valid."""

    def test_setup_script_exists(self):
        """Test that the setup script exists."""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'setup_gcp_resources.py'
        )
        assert os.path.exists(script_path), "Setup script should exist"

    def test_deployment_script_exists(self):
        """Test that the deployment script exists and is executable."""
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'deploy_gcp_infrastructure.sh'
        )

        assert os.path.exists(script_path), "Deployment script should exist"
        assert os.access(script_path, os.X_OK), "Deployment script should be executable"

if __name__ == '__main__':
    pytest.main([__file__])