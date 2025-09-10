"""
Test BigQuery Integration Module (gc08)

Tests for BigQuery analytics with caching and data explorer integration.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import os

# Mock environment variables
os.environ['REDIS_URL'] = 'redis://localhost:6379'
os.environ['BIGQUERY_CACHE_TTL'] = '3600'
os.environ['BIGQUERY_COST_THRESHOLD'] = '1048576'

from app.api.bigquery_analytics import router as bigquery_router
from app.api.data_explorer import router as data_explorer_router
from app.config.gcp_config import gcp_config


class TestBigQueryAnalytics:
    """Test BigQuery analytics with caching functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(bigquery_router)
        
    @patch('app.api.bigquery_analytics.gcp_config')
    @patch('app.api.bigquery_analytics.get_redis_client')
    def test_bigquery_query_with_caching(self, mock_redis, mock_gcp_config):
        """Test BigQuery query execution with caching."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = None  # No cache hit
        mock_redis_client.setex.return_value = True
        mock_redis.return_value = mock_redis_client
        
        # Mock BigQuery client
        mock_bq_client = Mock()
        mock_gcp_config.bigquery_client = mock_bq_client
        mock_gcp_config.project_id = "test-project"
        mock_gcp_config.bigquery_dataset = "test_dataset"
        
        # Mock query job and results
        mock_job = Mock()
        mock_job.result.return_value = [
            {"actor_id": "user1", "total_statements": 10},
            {"actor_id": "user2", "total_statements": 5}
        ]
        mock_bq_client.query.return_value = mock_job
        
        # Test query
        response = self.client.get("/bigquery/query?query=SELECT * FROM test_table&chart_type=table")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["chart_type"] == "table"
        assert data["row_count"] == 2
        assert data["cached"] is False
        assert data["cache_hit"] is False
        assert "cost_estimate" in data
        assert "cache_key" in data
        
        # Verify caching was attempted
        mock_redis_client.setex.assert_called_once()
    
    @patch('app.api.bigquery_analytics.gcp_config')
    @patch('app.api.bigquery_analytics.get_redis_client')
    def test_bigquery_query_cache_hit(self, mock_redis, mock_gcp_config):
        """Test BigQuery query with cache hit."""
        # Mock Redis client with cache hit
        mock_redis_client = Mock()
        cached_data = {
            "success": True,
            "results": [{"actor_id": "user1", "total_statements": 10}],
            "row_count": 1,
            "execution_time": 0.5,
            "query": "SELECT * FROM test_table"
        }
        mock_redis_client.get.return_value = json.dumps(cached_data)
        mock_redis.return_value = mock_redis_client
        
        # Test query
        response = self.client.get("/bigquery/query?query=SELECT * FROM test_table&chart_type=table")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cached"] is True
        assert data["cache_hit"] is True
        assert data["row_count"] == 1
        
        # Verify BigQuery was not called
        mock_gcp_config.bigquery_client.query.assert_not_called()
    
    @patch('app.api.bigquery_analytics.gcp_config')
    def test_bigquery_connection_status(self, mock_gcp_config):
        """Test BigQuery connection status endpoint."""
        # Mock BigQuery client and dataset
        mock_bq_client = Mock()
        mock_gcp_config.bigquery_client = mock_bq_client
        mock_gcp_config.project_id = "test-project"
        mock_gcp_config.bigquery_dataset = "test_dataset"
        
        # Mock dataset and tables
        mock_dataset = Mock()
        mock_bq_client.get_dataset.return_value = mock_dataset
        
        mock_table = Mock()
        mock_table.num_rows = 1000
        mock_table.num_bytes = 1024000
        mock_table.created = datetime.now()
        mock_table.modified = datetime.now()
        mock_bq_client.get_table.return_value = mock_table
        
        mock_tables = [Mock(table_id="statements"), Mock(table_id="actors")]
        mock_bq_client.list_tables.return_value = mock_tables
        
        response = self.client.get("/bigquery/connection-status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["project_id"] == "test-project"
        assert data["dataset_id"] == "test_dataset"
        assert data["tables_count"] == 2
    
    @patch('app.api.bigquery_analytics.gcp_config')
    @patch('app.api.bigquery_analytics.get_redis_client')
    def test_bigquery_integration_status(self, mock_redis, mock_gcp_config):
        """Test BigQuery integration status endpoint."""
        # Mock Redis client
        mock_redis_client = Mock()
        mock_redis_client.keys.return_value = ["bq_cache:key1", "bq_cache:key2"]
        mock_redis_client.info.return_value = {"used_memory_human": "1MB"}
        mock_redis.return_value = mock_redis_client
        
        # Mock BigQuery connection status
        with patch('app.api.bigquery_analytics.get_bigquery_connection_status') as mock_conn_status:
            mock_conn_status.return_value = {
                "status": "connected",
                "project_id": "test-project",
                "dataset_id": "test_dataset"
            }
            
            response = self.client.get("/bigquery/integration-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "bigquery-integration"
            assert data["cache_performance"]["cache_keys"] == 2
            assert data["cost_optimization"]["cache_hit_rate"] == "60-80%"


class TestDataExplorerBigQuery:
    """Test Data Explorer BigQuery integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(data_explorer_router)
    
    @patch('app.api.data_explorer.gcp_config')
    def test_bigquery_query_in_data_explorer(self, mock_gcp_config):
        """Test BigQuery query execution in data explorer."""
        # Mock BigQuery client
        mock_bq_client = Mock()
        mock_gcp_config.bigquery_client = mock_bq_client
        
        # Mock query job and results
        mock_job = Mock()
        mock_job.result.return_value = [
            {"actor_id": "user1", "verb_display": "completed"},
            {"actor_id": "user2", "verb_display": "started"}
        ]
        mock_bq_client.query.return_value = mock_job
        
        # Test query
        query_data = {
            "query": "SELECT actor_id, verb_display FROM statements LIMIT 10",
            "use_cache": True,
            "limit": 1000
        }
        
        response = self.client.post("/data-explorer/bigquery-query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_count"] == 2
        assert data["data"]["data_source"] == "bigquery"
        assert "execution_time" in data["data"]
    
    @patch('app.api.data_explorer.gcp_config')
    def test_bigquery_tables_endpoint(self, mock_gcp_config):
        """Test BigQuery tables listing endpoint."""
        # Mock BigQuery client
        mock_bq_client = Mock()
        mock_gcp_config.bigquery_client = mock_bq_client
        mock_gcp_config.bigquery_dataset = "test_dataset"
        mock_gcp_config.project_id = "test-project"
        
        # Mock dataset and tables
        mock_dataset = Mock()
        mock_bq_client.dataset.return_value = mock_dataset
        
        mock_table = Mock()
        mock_table.table_id = "statements"
        mock_table.num_rows = 1000
        mock_table.num_bytes = 1024000
        mock_table.created = datetime.now()
        mock_table.modified = datetime.now()
        mock_bq_client.get_table.return_value = mock_table
        
        mock_tables = [Mock(table_id="statements")]
        mock_bq_client.list_tables.return_value = mock_tables
        
        response = self.client.get("/data-explorer/bigquery-tables")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tables"]) == 1
        assert data["tables"][0]["table_name"] == "statements"
        assert data["dataset"] == "test_dataset"
        assert data["project"] == "test-project"
    
    def test_bigquery_query_validation(self):
        """Test BigQuery query validation (read-only queries only)."""
        # Test with invalid query (INSERT)
        query_data = {
            "query": "INSERT INTO statements VALUES ('test')",
            "use_cache": True,
            "limit": 1000
        }
        
        response = self.client.post("/data-explorer/bigquery-query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Only SELECT queries are allowed" in data["message"]


class TestCostOptimization:
    """Test cost optimization features."""
    
    def test_query_cost_estimation(self):
        """Test query cost estimation logic."""
        from app.api.bigquery_analytics import estimate_query_cost
        
        # Test simple query
        simple_query = "SELECT * FROM statements LIMIT 10"
        cost = estimate_query_cost(simple_query)
        
        assert "estimated_bytes" in cost
        assert "cost_factors" in cost
        assert "should_cache" in cost
        assert "cache_priority" in cost
        assert cost["should_cache"] is True
        
        # Test complex query
        complex_query = """
        SELECT a.actor_id, COUNT(*) as total
        FROM statements a
        JOIN actors b ON a.actor_id = b.actor_id
        WHERE DATE(a.timestamp) >= '2024-01-01'
        GROUP BY a.actor_id
        """
        cost = estimate_query_cost(complex_query)
        
        assert cost["cost_factors"]["scan_tables"] >= 2
        assert cost["cost_factors"]["complex_joins"] >= 1
        assert cost["cost_factors"]["aggregations"] >= 1
        assert cost["cost_factors"]["date_filters"] >= 1
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        from app.api.bigquery_analytics import generate_cache_key
        
        query1 = "SELECT * FROM statements"
        query2 = "SELECT * FROM statements"
        query3 = "SELECT * FROM actors"
        
        key1 = generate_cache_key(query1)
        key2 = generate_cache_key(query2)
        key3 = generate_cache_key(query3)
        
        # Same queries should generate same keys
        assert key1 == key2
        # Different queries should generate different keys
        assert key1 != key3
        # Keys should start with prefix
        assert key1.startswith("bq_cache:")
        
        # Test with parameters
        key_with_params = generate_cache_key(query1, {"limit": 10})
        key_without_params = generate_cache_key(query1)
        assert key_with_params != key_without_params


if __name__ == "__main__":
    pytest.main([__file__])
