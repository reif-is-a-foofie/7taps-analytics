"""
Tests for Cloud Function PUT method support.
Verifies that PUT requests work identically to POST requests for xAPI ingestion.
"""

import json
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app', 'api'))

from cloud_function_ingestion import cloud_ingest_xapi, validate_xapi_statement, publish_to_pubsub


class TestCloudFunctionPUTSupport:
    """Test suite for PUT method support in Cloud Function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.valid_xapi_statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/experienced"},
            "object": {"id": "http://example.com/activity"}
        }
        
        self.batch_xapi_statements = [
            {
                "actor": {"mbox": "mailto:user1@example.com"},
                "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
                "object": {"id": "http://example.com/lesson1"}
            },
            {
                "actor": {"mbox": "mailto:user2@example.com"},
                "verb": {"id": "http://adlnet.gov/expapi/verbs/attempted"},
                "object": {"id": "http://example.com/lesson2"}
            }
        ]

    def create_mock_request(self, method, data):
        """Create a mock request object for testing."""
        mock_request = Mock()
        mock_request.method = method
        mock_request.data = json.dumps(data).encode('utf-8')
        mock_request.get_json.return_value = data
        return mock_request

    def test_put_method_accepts_valid_single_statement(self):
        """Test that PUT method accepts valid single xAPI statement."""
        # Mock the entire publish_to_pubsub function to avoid JSON serialization issues
        with patch('cloud_function_ingestion.publish_to_pubsub') as mock_publish:
            mock_publish.return_value = {
                "success": True,
                "message_id": "test-message-id",
                "topic": "projects/taps-data/topics/xapi-ingestion-topic"
            }
            
            mock_request = self.create_mock_request('PUT', self.valid_xapi_statement)
            
            response_json, status_code = cloud_ingest_xapi(mock_request)
            
            assert status_code == 200
            response_data = json.loads(response_json)
            assert response_data['status'] == 'success'
            assert response_data['method'] == 'PUT'
            assert 'Successfully ingested 1 xAPI statement(s) via PUT' in response_data['message']
            assert len(response_data['results']) == 1
            assert response_data['results'][0]['success'] is True

    def test_put_method_accepts_valid_batch_statements(self):
        """Test that PUT method accepts valid batch xAPI statements."""
        # Mock the entire publish_to_pubsub function to avoid JSON serialization issues
        with patch('cloud_function_ingestion.publish_to_pubsub') as mock_publish:
            mock_publish.return_value = {
                "success": True,
                "message_id": "test-message-id",
                "topic": "projects/taps-data/topics/xapi-ingestion-topic"
            }
            
            mock_request = self.create_mock_request('PUT', self.batch_xapi_statements)
            
            response_json, status_code = cloud_ingest_xapi(mock_request)
            
            assert status_code == 200
            response_data = json.loads(response_json)
            assert response_data['status'] == 'success'
            assert response_data['method'] == 'PUT'
            assert 'Successfully ingested 2 xAPI statement(s) via PUT' in response_data['message']
            assert len(response_data['results']) == 2

    def test_put_method_rejects_invalid_json(self):
        """Test that PUT method rejects invalid JSON."""
        mock_request = Mock()
        mock_request.method = 'PUT'
        mock_request.data = b'invalid json'
        mock_request.get_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 400
        response_data = json.loads(response_json)
        assert response_data['error'] == 'Invalid JSON'

    def test_put_method_rejects_invalid_xapi_statement(self):
        """Test that PUT method rejects invalid xAPI statements."""
        invalid_statement = {
            "actor": {"mbox": "mailto:test@example.com"},
            # Missing required 'verb' and 'object' fields
        }
        
        mock_request = self.create_mock_request('PUT', invalid_statement)
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 400
        response_data = json.loads(response_json)
        assert response_data['error'] == 'Invalid xAPI statements'
        assert 'required_fields' in response_data

    def test_put_method_handles_mixed_valid_invalid_statements(self):
        """Test that PUT method handles batch with mixed valid/invalid statements."""
        mixed_statements = [
            self.valid_xapi_statement,  # Valid
            {"actor": {"mbox": "mailto:test@example.com"}},  # Invalid - missing verb/object
            self.valid_xapi_statement   # Valid
        ]
        
        mock_request = self.create_mock_request('PUT', mixed_statements)
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 400
        response_data = json.loads(response_json)
        assert response_data['error'] == 'Invalid xAPI statements'
        assert 'indices [1]' in response_data['message']

    def test_put_method_rejects_unsupported_methods(self):
        """Test that PUT method rejects unsupported HTTP methods."""
        mock_request = Mock()
        mock_request.method = 'GET'
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 405
        response_data = json.loads(response_json)
        assert response_data['error'] == 'Method not allowed'
        assert 'POST and PUT requests are accepted' in response_data['message']
        assert 'supported_methods' in response_data

    def test_put_method_handles_options_request(self):
        """Test that PUT method handles OPTIONS preflight requests."""
        mock_request = Mock()
        mock_request.method = 'OPTIONS'
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 200
        response_data = json.loads(response_json)
        assert response_data['status'] == 'ok'

    def test_put_method_publishes_to_pubsub_successfully(self):
        """Test that PUT method successfully publishes to Pub/Sub."""
        # Mock the entire publish_to_pubsub function to avoid JSON serialization issues
        with patch('cloud_function_ingestion.publish_to_pubsub') as mock_publish:
            mock_publish.return_value = {
                "success": True,
                "message_id": "test-message-id-123",
                "topic": "projects/taps-data/topics/xapi-ingestion-topic"
            }
            
            mock_request = self.create_mock_request('PUT', self.valid_xapi_statement)
            
            response_json, status_code = cloud_ingest_xapi(mock_request)
            
            assert status_code == 200
            response_data = json.loads(response_json)
            
            # Verify publish_to_pubsub was called
            mock_publish.assert_called_once_with(self.valid_xapi_statement, source='cloud_function_http')

    def test_put_vs_post_identical_behavior(self):
        """Test that PUT and POST methods behave identically."""
        # Mock the entire publish_to_pubsub function to avoid JSON serialization issues
        with patch('cloud_function_ingestion.publish_to_pubsub') as mock_publish:
            mock_publish.return_value = {
                "success": True,
                "message_id": "test-message-id",
                "topic": "projects/taps-data/topics/xapi-ingestion-topic"
            }
            
            # Test POST
            post_request = self.create_mock_request('POST', self.valid_xapi_statement)
            post_response_json, post_status_code = cloud_ingest_xapi(post_request)
            
            # Test PUT
            put_request = self.create_mock_request('PUT', self.valid_xapi_statement)
            put_response_json, put_status_code = cloud_ingest_xapi(put_request)
            
            # Both should succeed
            assert post_status_code == 200
            assert put_status_code == 200
            
            # Parse responses
            post_data = json.loads(post_response_json)
            put_data = json.loads(put_response_json)
            
            # Both should have same structure (except method field)
            assert post_data['status'] == put_data['status']
            assert post_data['results'][0]['success'] == put_data['results'][0]['success']
            assert post_data['results'][0]['message_id'] == put_data['results'][0]['message_id']
            
            # Only difference should be the method field
            assert post_data['method'] == 'POST'
            assert put_data['method'] == 'PUT'

    @patch('cloud_function_ingestion.publisher', None)
    @patch('cloud_function_ingestion.topic_path', None)
    def test_put_method_handles_pubsub_failure(self):
        """Test that PUT method handles Pub/Sub publishing failures gracefully."""
        mock_request = self.create_mock_request('PUT', self.valid_xapi_statement)
        
        response_json, status_code = cloud_ingest_xapi(mock_request)
        
        assert status_code == 500
        response_data = json.loads(response_json)
        assert response_data['error'] == 'Internal server error'
        assert 'Pub/Sub client not initialized' in response_data['message']

    def test_validate_xapi_statement_function(self):
        """Test the validate_xapi_statement helper function."""
        # Valid statement
        assert validate_xapi_statement(self.valid_xapi_statement) is True
        
        # Invalid statements
        assert validate_xapi_statement({"actor": {"mbox": "mailto:test@example.com"}}) is False
        assert validate_xapi_statement({"verb": {"id": "http://example.com/verb"}}) is False
        assert validate_xapi_statement({"object": {"id": "http://example.com/object"}}) is False
        assert validate_xapi_statement({}) is False

    def test_put_method_response_includes_timestamp(self):
        """Test that PUT method response includes timestamp."""
        with patch('cloud_function_ingestion.publish_to_pubsub') as mock_publish:
            mock_publish.return_value = {
                "success": True,
                "message_id": "test-message-id",
                "topic": "projects/taps-data/topics/xapi-ingestion-topic"
            }
            
            mock_request = self.create_mock_request('PUT', self.valid_xapi_statement)
            
            response_json, status_code = cloud_ingest_xapi(mock_request)
            
            assert status_code == 200
            response_data = json.loads(response_json)
            assert 'timestamp' in response_data
            
            # Verify timestamp is valid ISO format
            timestamp = datetime.fromisoformat(response_data['timestamp'].replace('Z', '+00:00'))
            assert isinstance(timestamp, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

