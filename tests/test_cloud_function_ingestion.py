"""
Tests for Cloud Function xAPI ingestion.
Tests the HTTP endpoint, xAPI validation, and Pub/Sub publishing.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from app.api.cloud_function_ingestion import (
    validate_xapi_statement,
    publish_to_pubsub,
    cloud_ingest_xapi,
    get_cloud_function_status
)
from app.config.gcp_config import gcp_config


class TestXAPIValidation:
    """Test xAPI statement validation."""

    def test_valid_xapi_statement(self):
        """Test validation of valid xAPI statement."""
        statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity/1"}
        }
        assert validate_xapi_statement(statement) == True

    def test_invalid_xapi_statement_missing_actor(self):
        """Test validation fails when actor is missing."""
        statement = {
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity/1"}
        }
        assert validate_xapi_statement(statement) == False

    def test_invalid_xapi_statement_missing_verb(self):
        """Test validation fails when verb is missing."""
        statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "object": {"id": "http://example.com/activity/1"}
        }
        assert validate_xapi_statement(statement) == False

    def test_invalid_xapi_statement_missing_object(self):
        """Test validation fails when object is missing."""
        statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"}
        }
        assert validate_xapi_statement(statement) == False


class TestPubSubPublishing:
    """Test Pub/Sub publishing functionality."""

    @patch('app.api.cloud_function_ingestion.gcp_config')
    def test_successful_pubsub_publish(self, mock_gcp_config):
        """Test successful publishing to Pub/Sub."""
        # Mock the GCP config
        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "message-123"
        mock_publisher.publish.return_value = mock_future
        mock_gcp_config.pubsub_publisher = mock_publisher
        mock_gcp_config.get_topic_path.return_value = "projects/test/topics/xapi-ingestion-topic"

        statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity/1"}
        }

        result = publish_to_pubsub(statement)

        assert result["success"] == True
        assert result["message_id"] == "message-123"
        assert "topic" in result

    @patch('app.api.cloud_function_ingestion.gcp_config')
    def test_pubsub_topic_not_found(self, mock_gcp_config):
        """Test handling when Pub/Sub topic doesn't exist."""
        from google.api_core import exceptions as gcp_exceptions

        mock_publisher = MagicMock()
        mock_publisher.publish.side_effect = gcp_exceptions.NotFound("Topic not found")
        mock_gcp_config.pubsub_publisher = mock_publisher
        mock_gcp_config.pubsub_topic = "nonexistent-topic"

        statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity/1"}
        }

        with pytest.raises(Exception) as exc_info:
            publish_to_pubsub(statement)

        assert "Pub/Sub topic not found" in str(exc_info.value)


class TestCloudFunctionEndpoints:
    """Test Cloud Function HTTP endpoints."""

    @patch('app.api.cloud_function_ingestion.publish_to_pubsub')
    def test_cloud_ingest_xapi_success(self, mock_publish):
        """Test successful xAPI ingestion."""
        mock_publish.return_value = {
            "success": True,
            "message_id": "message-123",
            "topic": "projects/test/topics/xapi-ingestion-topic"
        }

        # Mock request object
        request = Mock()
        request.method = 'POST'
        request.get_json.return_value = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity/1"}
        }

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 200
        assert response_data["status"] == "success"
        assert "Successfully ingested 1 xAPI statement" in response_data["message"]

    def test_cloud_ingest_xapi_invalid_method(self):
        """Test rejection of non-POST requests."""
        request = Mock()
        request.method = 'GET'

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 405
        assert response_data["error"] == "Method not allowed"

    def test_cloud_ingest_xapi_invalid_json(self):
        """Test handling of invalid JSON."""
        request = Mock()
        request.method = 'POST'
        request.get_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 400
        assert "Invalid JSON" in response_data["message"]

    def test_cloud_ingest_xapi_invalid_xapi_statement(self):
        """Test rejection of invalid xAPI statements."""
        request = Mock()
        request.method = 'POST'
        request.get_json.return_value = {
            "actor": {"mbox": "mailto:test@example.com"},
            # Missing verb and object
        }

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 400
        assert response_data["error"] == "Invalid xAPI statements"

    def test_cloud_ingest_xapi_options_request(self):
        """Test CORS preflight OPTIONS request."""
        request = Mock()
        request.method = 'OPTIONS'

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 200
        assert response_data["status"] == "ok"


class TestCloudFunctionStatus:
    """Test Cloud Function status endpoint."""

    @patch('app.api.cloud_function_ingestion.gcp_config')
    def test_cloud_function_status_healthy(self, mock_gcp_config):
        """Test healthy status response."""
        mock_gcp_config.validate_config.return_value = {
            "project_id": "test-project",
            "pubsub_topic": "test-topic",
            "location": "us-central1",
            "service_account_loaded": True,
            "pubsub_topic_exists": True,
            "credentials_valid": True,
            "errors": []
        }
        mock_gcp_config.location = "us-central1"

        response_json, status_code = get_cloud_function_status()

        response_data = json.loads(response_json)
        assert status_code == 200
        assert response_data["status"] == "healthy"
        assert response_data["function_status"]["function_name"] == "cloud_ingest_xapi"

    @patch('app.api.cloud_function_ingestion.gcp_config')
    def test_cloud_function_status_unhealthy(self, mock_gcp_config):
        """Test unhealthy status response."""
        mock_gcp_config.validate_config.return_value = {
            "project_id": "test-project",
            "pubsub_topic": "test-topic",
            "location": "us-central1",
            "service_account_loaded": False,
            "pubsub_topic_exists": False,
            "credentials_valid": False,
            "errors": ["Topic not found"]
        }
        mock_gcp_config.location = "us-central1"

        response_json, status_code = get_cloud_function_status()

        response_data = json.loads(response_json)
        assert status_code == 503
        assert response_data["status"] == "unhealthy"


class TestBatchIngestion:
    """Test batch xAPI statement ingestion."""

    @patch('app.api.cloud_function_ingestion.publish_to_pubsub')
    def test_batch_ingestion_success(self, mock_publish):
        """Test successful batch ingestion."""
        mock_publish.return_value = {
            "success": True,
            "message_id": "message-123",
            "topic": "projects/test/topics/xapi-ingestion-topic"
        }

        request = Mock()
        request.method = 'POST'
        request.get_json.return_value = [
            {
                "actor": {"mbox": "mailto:user1@example.com"},
                "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
                "object": {"id": "http://example.com/activity/1"}
            },
            {
                "actor": {"mbox": "mailto:user2@example.com"},
                "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
                "object": {"id": "http://example.com/activity/2"}
            }
        ]

        response_json, status_code = cloud_ingest_xapi(request)

        response_data = json.loads(response_json)
        assert status_code == 200
        assert response_data["status"] == "success"
        assert "Successfully ingested 2 xAPI statement" in response_data["message"]
        assert len(response_data["results"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])
