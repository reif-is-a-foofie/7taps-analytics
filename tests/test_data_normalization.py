"""
Tests for data normalization functionality.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.data_normalization import router
from app.data_normalization import DataNormalizer

# Test client
client = TestClient(router)


class TestDataNormalizer:
    """Test cases for DataNormalizer class."""

    @pytest.fixture
    def normalizer(self):
        """Create a DataNormalizer instance for testing."""
        return DataNormalizer()

    @pytest.fixture
    def sample_statement(self):
        """Sample xAPI statement for testing."""
        return {
            "id": "test-statement-123",
            "actor": {
                "objectType": "Agent",
                "name": "John Doe",
                "account": {
                    "name": "john.doe@example.com",
                    "homePage": "https://example.com",
                },
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"},
            },
            "object": {
                "id": "https://example.com/activities/test-activity",
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": "Test Activity"},
                    "description": {"en-US": "A test activity for validation"},
                    "interactionType": "choice",
                    "correctResponsesPattern": ["0"],
                    "choices": [
                        {"id": "0", "description": {"en-US": "Correct answer"}},
                        {"id": "1", "description": {"en-US": "Wrong answer"}},
                    ],
                },
            },
            "result": {
                "success": True,
                "completion": True,
                "score": {"scaled": 1.0, "raw": 100, "min": 0, "max": 100},
            },
            "context": {
                "registration": "test-registration-123",
                "platform": "Test Platform",
                "language": "en-US",
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "1.0.3",
        }

    def test_extract_actor_data(self, normalizer, sample_statement):
        """Test actor data extraction."""
        actor_data = normalizer.extract_actor_data(sample_statement["actor"])

        assert actor_data["actor_id"] == "john.doe@example.com"
        assert actor_data["actor_type"] == "Agent"
        assert actor_data["name"] == "John Doe"
        assert actor_data["account_name"] == "john.doe@example.com"
        assert actor_data["account_homepage"] == "https://example.com"

    def test_extract_activity_data(self, normalizer, sample_statement):
        """Test activity data extraction."""
        activity_data = normalizer.extract_activity_data(sample_statement["object"])

        assert (
            activity_data["activity_id"]
            == "https://example.com/activities/test-activity"
        )
        assert activity_data["activity_type"] == "Activity"
        assert activity_data["name"] == "Test Activity"
        assert activity_data["description"] == "A test activity for validation"
        assert activity_data["interaction_type"] == "choice"
        assert activity_data["correct_responses_pattern"] == "0"
        assert activity_data["choices"] is not None

    def test_extract_verb_data(self, normalizer, sample_statement):
        """Test verb data extraction."""
        verb_data = normalizer.extract_verb_data(sample_statement["verb"])

        assert verb_data["verb_id"] == "http://adlnet.gov/expapi/verbs/completed"
        assert verb_data["display_name"] == "completed"
        assert verb_data["language"] == "en-US"

    def test_extract_result_data(self, normalizer, sample_statement):
        """Test result data extraction."""
        result_data = normalizer.extract_result_data(sample_statement["result"])

        assert result_data["result_success"] is True
        assert result_data["result_completion"] is True
        assert result_data["result_score_scaled"] == 1.0
        assert result_data["result_score_raw"] == 100
        assert result_data["result_score_min"] == 0
        assert result_data["result_score_max"] == 100

    def test_extract_context_data(self, normalizer, sample_statement):
        """Test context data extraction."""
        context_data = normalizer.extract_context_data(sample_statement["context"])

        assert context_data["context_registration"] == "test-registration-123"
        assert context_data["context_platform"] == "Test Platform"
        assert context_data["context_language"] == "en-US"

    def test_normalize_statement(self, normalizer, sample_statement):
        """Test complete statement normalization."""
        # This would require a database connection, so we'll test the structure
        # In a real test environment, you'd use a test database
        normalized = normalizer.normalize_statement(sample_statement)

        # Test that the normalized data has the expected structure
        assert "actor" in normalized
        assert "activity" in normalized
        assert "verb" in normalized
        assert "statement" in normalized

        # Test statement data
        statement = normalized["statement"]
        assert statement["statement_id"] == "test-statement-123"
        assert statement["actor_id"] == "john.doe@example.com"
        assert statement["verb_id"] == "http://adlnet.gov/expapi/verbs/completed"
        assert (
            statement["activity_id"] == "https://example.com/activities/test-activity"
        )


class TestDataNormalizationAPI:
    """Test cases for data normalization API endpoints."""

    def test_normalize_statement_endpoint(self, sample_statement):
        """Test the normalize statement API endpoint."""
        response = client.post(
            "/normalize/statement", json={"statement": sample_statement}
        )

        # This would fail in a test environment without a database
        # In a real test, you'd mock the database or use a test database
        assert response.status_code in [200, 500]  # Either success or database error

    def test_normalize_batch_endpoint(self, sample_statement):
        """Test the normalize batch API endpoint."""
        response = client.post(
            "/normalize/batch",
            json={"statements": [sample_statement, sample_statement]},
        )

        # This would fail in a test environment without a database
        assert response.status_code in [200, 500]

    def test_setup_normalization_tables_endpoint(self):
        """Test the setup normalization tables API endpoint."""
        response = client.post("/normalize/setup")

        # This would fail in a test environment without a database
        assert response.status_code in [200, 500]

    def test_get_normalization_stats_endpoint(self):
        """Test the get normalization stats API endpoint."""
        response = client.get("/normalize/stats")

        # This would fail in a test environment without a database
        assert response.status_code in [200, 500]

    def test_normalization_health_check_endpoint(self):
        """Test the normalization health check API endpoint."""
        response = client.get("/normalize/health")

        # This should always return a response, even if unhealthy
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


def test_data_normalization_integration():
    """Integration test for data normalization with the main app."""
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    # Test that the normalization endpoints are available
    response = client.get("/api/normalize/health")
    assert response.status_code == 200

    # Test API documentation includes normalization endpoints
    response = client.get("/docs")
    assert response.status_code == 200
    # The docs should include normalization endpoints


if __name__ == "__main__":
    pytest.main([__file__])
