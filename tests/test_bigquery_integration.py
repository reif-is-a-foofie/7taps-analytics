"""BigQuery analytics integration tests focused on caching utilities."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.bigquery_analytics import router as bigquery_router


class TestBigQueryAnalytics:
    """Validate the BigQuery analytics endpoints and helpers."""

    def setup_method(self):
        self.client = TestClient(bigquery_router)

    @patch('app.api.bigquery_analytics.get_gcp_config')
    @patch('app.api.bigquery_analytics.get_redis_client')
    def test_bigquery_query_with_caching(self, mock_get_redis, mock_get_config):
        """Query endpoint should populate cache when no cached entry exists."""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        mock_bq_client = Mock()
        mock_job = Mock()
        mock_job.result.return_value = [
            {"actor_id": "user1", "total_statements": 10},
            {"actor_id": "user2", "total_statements": 5},
        ]
        mock_bq_client.query.return_value = mock_job
        mock_config = Mock()
        mock_config.bigquery_client = mock_bq_client
        mock_config.project_id = "test-project"
        mock_config.bigquery_dataset = "test_dataset"
        mock_get_config.return_value = mock_config

        response = self.client.get(
            "/bigquery/query",
            params={"query": "SELECT * FROM statements", "chart_type": "table"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cache_hit"] is False
        assert data["row_count"] == 2
        mock_redis.setex.assert_called_once()

    @patch('app.api.bigquery_analytics.get_gcp_config')
    @patch('app.api.bigquery_analytics.get_redis_client')
    def test_bigquery_query_cache_hit(self, mock_get_redis, mock_get_config):
        """Query endpoint should short-circuit when cached data exists."""
        cached_payload = {
            "success": True,
            "row_count": 1,
            "results": [{"actor_id": "user1", "total_statements": 10}],
            "query": "SELECT * FROM statements",
            "cached": True,
        }
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps(cached_payload)
        mock_get_redis.return_value = mock_redis

        mock_config = Mock()
        mock_config.bigquery_client = Mock()
        mock_get_config.return_value = mock_config

        response = self.client.get(
            "/bigquery/query",
            params={"query": "SELECT * FROM statements", "chart_type": "table"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is True
        mock_config.bigquery_client.query.assert_not_called()

    @patch('app.api.bigquery_analytics.get_gcp_config')
    def test_bigquery_connection_status(self, mock_get_config):
        """Connection status endpoint should report dataset metadata."""
        mock_bq_client = Mock()
        mock_config = Mock()
        mock_config.bigquery_client = mock_bq_client
        mock_config.project_id = "test-project"
        mock_config.bigquery_dataset = "test_dataset"
        mock_get_config.return_value = mock_config

        mock_table = Mock()
        mock_table.num_rows = 100
        mock_table.num_bytes = 2048
        mock_table.created = datetime.utcnow()
        mock_table.modified = datetime.utcnow()
        mock_bq_client.get_table.return_value = mock_table
        mock_bq_client.list_tables.return_value = [Mock(table_id="statements"), Mock(table_id="actors")]

        response = self.client.get("/bigquery/connection-status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["tables_count"] == 2

    def test_cache_key_generation(self):
        """Cache keys should reflect query text and parameters."""
        from app.api.bigquery_analytics import generate_cache_key

        key1 = generate_cache_key("SELECT * FROM statements", {"limit": 10})
        key2 = generate_cache_key("SELECT * FROM statements", {"limit": 10})
        key3 = generate_cache_key("SELECT * FROM statements", {"limit": 20})

        assert key1 == key2
        assert key1 != key3
        assert key1.startswith("bq_cache:")


if __name__ == "__main__":
    pytest.main([__file__])
