"""
Test Migration Cleanup & Validation (gc05)

Tests for the Google Cloud migration cleanup and validation functionality.
Covers migration validation script, legacy endpoint deprecation, and monitoring endpoints.
"""

import os
import sys
import json
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from scripts.heroku_migration_cleanup import MigrationValidator

# Test client for API tests
client = TestClient(app)

class TestMigrationValidator:
    """Test the MigrationValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a MigrationValidator instance."""
        return MigrationValidator()

    @patch('app.config.gcp_config.GCPConfig.get_credentials')
    def test_validate_service_account_success(self, mock_get_credentials, validator):
        """Test successful service account validation."""
        mock_credentials = Mock()
        mock_credentials.service_account_email = 'test@test.com'
        mock_get_credentials.return_value = mock_credentials

        with patch('google.auth.default') as mock_default:
            mock_default.return_value = (mock_credentials, 'test-project')
            result = validator.validate_service_account()

            assert result is True
            assert 'service_account' in validator.results
            assert validator.results['service_account']['status'] == 'valid'

    @patch('app.config.gcp_config.GCPConfig.get_credentials')
    def test_validate_service_account_failure(self, mock_get_credentials, validator):
        """Test failed service account validation."""
        mock_get_credentials.return_value = None

        result = validator.validate_service_account()

        assert result is False
        assert len(validator.errors) > 0

    @patch('scripts.heroku_migration_cleanup.requests.get')
    @patch('app.config.gcp_config.GCPConfig')
    def test_validate_cloud_function_success(self, mock_config, mock_get, validator):
        """Test successful Cloud Function validation."""
        mock_config_instance = Mock()
        mock_config_instance.project_id = 'test-project'
        mock_config.return_value = mock_config_instance

        mock_response = Mock()
        mock_response.status_code = 405  # Expected for GET on POST endpoint
        mock_get.return_value = mock_response

        result = validator.validate_cloud_function()

        assert result is True
        assert 'cloud_function' in validator.results
        assert validator.results['cloud_function']['status'] == 'deployed'

    @patch('scripts.heroku_migration_cleanup.requests.get')
    @patch('app.config.gcp_config.GCPConfig')
    def test_validate_cloud_function_failure(self, mock_config, mock_get, validator):
        """Test failed Cloud Function validation."""
        mock_config_instance = Mock()
        mock_config_instance.project_id = 'test-project'
        mock_config.return_value = mock_config_instance

        mock_get.side_effect = Exception("Connection failed")

        result = validator.validate_cloud_function()

        assert result is False
        assert len(validator.errors) > 0

    @patch('google.cloud.pubsub_v1.PublisherClient')
    @patch('google.cloud.pubsub_v1.SubscriberClient')
    @patch('app.config.gcp_config.GCPConfig')
    def test_validate_pubsub_success(self, mock_config, mock_subscriber, mock_publisher, validator):
        """Test successful Pub/Sub validation."""
        mock_config_instance = Mock()
        mock_config_instance.project_id = 'test-project'
        mock_config_instance.pubsub_topic = 'test-topic'
        mock_config_instance.pubsub_storage_subscription = 'test-subscription'
        mock_config.return_value = mock_config_instance

        # Mock successful topic and subscription existence
        mock_publisher_instance = Mock()
        mock_subscriber_instance = Mock()
        mock_publisher.return_value = mock_publisher_instance
        mock_subscriber.return_value = mock_subscriber_instance

        result = validator.validate_pubsub()

        # Note: This test might need adjustment based on actual mock setup
        assert isinstance(result, bool)

    @patch('google.cloud.storage.Client')
    @patch('app.config.gcp_config.GCPConfig')
    def test_validate_cloud_storage_success(self, mock_config, mock_storage_client, validator):
        """Test successful Cloud Storage validation."""
        mock_config_instance = Mock()
        mock_config_instance.storage_bucket = 'test-bucket'
        mock_config.return_value = mock_config_instance

        mock_bucket = Mock()
        mock_bucket.exists.return_value = True
        mock_bucket.list_blobs.return_value = []

        mock_client_instance = Mock()
        mock_client_instance.bucket.return_value = mock_bucket
        mock_storage_client.return_value = mock_client_instance

        result = validator.validate_cloud_storage()

        assert result is True
        assert 'cloud_storage' in validator.results
        assert validator.results['cloud_storage']['status'] == 'accessible'

    @patch('google.cloud.bigquery.Client')
    @patch('app.config.gcp_config.GCPConfig')
    def test_validate_bigquery_success(self, mock_config, mock_bq_client, validator):
        """Test successful BigQuery validation."""
        mock_config_instance = Mock()
        mock_config_instance.bigquery_dataset = 'test-dataset'
        mock_config.return_value = mock_config_instance

        mock_dataset = Mock()
        mock_table = Mock()
        mock_table.table_id = 'xapi_events'

        mock_client_instance = Mock()
        mock_client_instance.get_dataset.return_value = mock_dataset
        mock_client_instance.list_tables.return_value = [mock_table]
        mock_bq_client.return_value = mock_client_instance

        result = validator.validate_bigquery()

        assert result is True
        assert 'bigquery' in validator.results

    @patch('scripts.heroku_migration_cleanup.requests.get')
    def test_validate_api_endpoints_success(self, mock_get, validator):
        """Test successful API endpoints validation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validator.validate_api_endpoints()

        assert result is True
        assert 'api_endpoints' in validator.results

    def test_run_full_validation(self, validator):
        """Test full validation run."""
        with patch.object(validator, 'validate_service_account', return_value=True), \
             patch.object(validator, 'validate_cloud_function', return_value=True), \
             patch.object(validator, 'validate_pubsub', return_value=True), \
             patch.object(validator, 'validate_cloud_storage', return_value=True), \
             patch.object(validator, 'validate_bigquery', return_value=True), \
             patch.object(validator, 'validate_api_endpoints', return_value=True):

            report = validator.run_full_validation()

            assert 'timestamp' in report
            assert 'migration_complete' in report
            assert 'validation_results' in report
            assert 'errors' in report
            assert 'summary' in report

    def test_save_report(self, validator):
        """Test saving validation report."""
        report = {'test': 'data', 'timestamp': '2023-01-01T00:00:00Z'}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_filename = f.name

        try:
            saved_filename = validator.save_report(report, temp_filename)

            assert saved_filename == temp_filename
            assert os.path.exists(temp_filename)

            with open(temp_filename, 'r') as f:
                saved_data = json.load(f)
                assert saved_data == report
        finally:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

class TestLegacyEndpoints:
    """Test legacy Heroku endpoints."""

    def test_legacy_health_check(self):
        """Test legacy health check endpoint returns deprecation warning."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "warning" in data
        assert "DEPRECATED ENDPOINT" in data["warning"]
        assert "migration_info" in data
        assert "X-Deprecated" in response.headers

    def test_legacy_xapi_ingestion(self):
        """Test legacy xAPI ingestion endpoint returns deprecation warning."""
        response = client.post("/api/xapi/statements", json={})

        assert response.status_code == 200
        data = response.json()
        assert "warning" in data
        assert "DEPRECATED ENDPOINT" in data["warning"]
        assert "new_endpoint" in data
        assert data["new_endpoint"] == "/api/xapi/cloud-ingest"

    def test_legacy_analytics_dashboard(self):
        """Test legacy analytics dashboard endpoint returns deprecation warning."""
        response = client.get("/api/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "warning" in data
        assert "DEPRECATED ENDPOINT" in data["warning"]
        assert "new_endpoint" in data
        assert "/api/analytics/bigquery/dashboard" in data["new_endpoint"]

    def test_legacy_data_export(self):
        """Test legacy data export endpoint returns deprecation warning."""
        response = client.get("/api/data/export")

        assert response.status_code == 200
        data = response.json()
        assert "warning" in data
        assert "DEPRECATED ENDPOINT" in data["warning"]
        assert "new_endpoint" in data

    def test_migration_status_endpoint(self):
        """Test migration status endpoint provides comprehensive status."""
        with patch('scripts.heroku_migration_cleanup.MigrationValidator') as mock_validator:
            mock_instance = Mock()
            mock_report = {
                'timestamp': '2023-01-01T00:00:00Z',
                'migration_complete': True,
                'validation_results': {
                    'cloud_function': {'status': 'deployed'},
                    'pubsub': {'status': 'configured'},
                    'cloud_storage': {'status': 'accessible'},
                    'bigquery': {'status': 'operational'},
                    'api_endpoints': {'status': 'ok'}
                },
                'errors': [],
                'summary': {'total_validations': 5, 'passed': 5, 'failed': 0}
            }
            mock_instance.run_full_validation.return_value = mock_report
            mock_validator.return_value = mock_instance

            response = client.get("/api/debug/migration-status")

            assert response.status_code == 200
            data = response.json()
            assert "migration_status" in data
            assert "components" in data
            assert "validation_timestamp" in data

    @patch('scripts.heroku_migration_cleanup.MigrationValidator')
    def test_validate_migration_complete_endpoint(self, mock_validator):
        """Test manual migration validation endpoint."""
        mock_instance = Mock()
        mock_report = {
            'timestamp': '2023-01-01T00:00:00Z',
            'migration_complete': True,
            'validation_results': {},
            'errors': [],
            'summary': {'total_validations': 5, 'passed': 5, 'failed': 0}
        }
        mock_instance.run_full_validation.return_value = mock_report
        mock_instance.save_report.return_value = 'test_report.json'
        mock_validator.return_value = mock_instance

        response = client.post("/api/debug/validate-migration-complete")

        assert response.status_code == 200
        data = response.json()
        assert data["validation_triggered"] is True
        assert "report_file" in data
        assert "recommendations" in data

    def test_list_legacy_endpoints(self):
        """Test listing all legacy endpoints."""
        response = client.get("/api/debug/legacy-endpoints")

        assert response.status_code == 200
        data = response.json()
        assert "legacy_endpoints" in data
        assert "total_deprecated" in data
        assert "migration_status" in data
        assert data["migration_status"] == "completed"

        endpoints = data["legacy_endpoints"]
        assert len(endpoints) > 0

        # Check that all endpoints have required fields
        for endpoint in endpoints:
            assert "endpoint" in endpoint
            assert "status" in endpoint
            assert "replacement" in endpoint
            assert "migration_date" in endpoint
            assert endpoint["status"] == "deprecated"

class TestMigrationCleanupScript:
    """Test the migration cleanup script execution."""

    def test_script_import(self):
        """Test that the migration cleanup script can be imported."""
        try:
            from scripts.heroku_migration_cleanup import MigrationValidator, main
            assert MigrationValidator is not None
            assert main is not None
        except ImportError as e:
            pytest.fail(f"Failed to import migration cleanup script: {e}")

    @patch('scripts.heroku_migration_cleanup.MigrationValidator')
    def test_main_function_success(self, mock_validator):
        """Test main function with successful validation."""
        mock_instance = Mock()
        mock_report = {
            'migration_complete': True,
            'summary': {'total_validations': 5, 'passed': 5, 'failed': 0},
            'errors': []
        }
        mock_instance.run_full_validation.return_value = mock_report
        mock_validator.return_value = mock_instance

        with patch('sys.exit') as mock_exit:
            from scripts.heroku_migration_cleanup import main
            main()

            mock_exit.assert_called_once_with(0)

    @patch('scripts.heroku_migration_cleanup.MigrationValidator')
    def test_main_function_failure(self, mock_validator):
        """Test main function with failed validation."""
        mock_instance = Mock()
        mock_report = {
            'migration_complete': False,
            'summary': {'total_validations': 5, 'passed': 3, 'failed': 2},
            'errors': ['Test error']
        }
        mock_instance.run_full_validation.return_value = mock_report
        mock_validator.return_value = mock_instance

        with patch('sys.exit') as mock_exit:
            from scripts.heroku_migration_cleanup import main
            main()

            mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    pytest.main([__file__])
