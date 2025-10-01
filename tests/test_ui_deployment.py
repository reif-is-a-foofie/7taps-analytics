"""
Test suite for UI deployment optimization (gc07).
Tests cost monitoring, BigQuery caching, and Cloud Run deployment.
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

from app.api.cost_monitoring import router as cost_monitoring_router
from app.config.cloud_run_config import CloudRunConfig, get_cost_optimized_config, get_performance_optimized_config

# Create a minimal test app to avoid import issues
test_app = FastAPI()
test_app.include_router(cost_monitoring_router, prefix="/api")

client = TestClient(test_app)

class TestCostMonitoring:
    """Test cost monitoring functionality."""
    
    def test_cost_monitoring_health(self):
        """Test cost monitoring health endpoint."""
        response = client.get("/api/cost/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "cost-monitoring" in data["service"]
        assert "/api/cost/current-usage" in data["endpoints"]
    
    @patch('app.api.cost_monitoring.get_bigquery_usage_stats')
    def test_current_usage_endpoint(self, mock_usage_stats):
        """Test current usage endpoint."""
        mock_usage_stats.return_value = {
            "total_bytes": 1000000,
            "total_rows": 1000,
            "tables_count": 5,
            "estimated_cost": 0.005,
            "last_updated": datetime.now().isoformat()
        }
        
        response = client.get("/api/cost/current-usage")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_usage" in data
        assert "optimization_score" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
    
    def test_query_cost_estimation(self):
        """Test query cost estimation."""
        test_query = "SELECT * FROM statements LIMIT 100"
        
        response = client.post("/api/cost/estimate-query", params={"query": test_query})
        assert response.status_code == 200
        
        data = response.json()
        assert "estimated_bytes" in data
        assert "estimated_cost" in data
        assert "optimization_suggestions" in data
        assert isinstance(data["optimization_suggestions"], list)
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations endpoint."""
        response = client.get("/api/cost/optimization-recommendations")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_usage" in data
        assert "recommendations" in data
        assert "estimated_monthly_savings" in data

class TestCloudRunConfiguration:
    """Test Cloud Run deployment configuration."""
    
    def test_default_cloud_run_config(self):
        """Test default Cloud Run configuration."""
        config = CloudRunConfig()
        
        assert config.service_name == "taps-analytics-ui"
        assert config.region == "us-central1"
        assert config.cpu == "1"
        assert config.memory == "2Gi"
        assert config.min_instances == 0
        assert config.max_instances == 10
    
    def test_cost_optimized_config(self):
        """Test cost-optimized configuration."""
        config = get_cost_optimized_config()
        
        assert config.cpu == "0.5"
        assert config.memory == "1Gi"
        assert config.min_instances == 0
        assert config.max_instances == 5
        assert config.cpu_throttling == True
        assert config.bigquery_cache_ttl == 7200
    
    def test_performance_optimized_config(self):
        """Test performance-optimized configuration."""
        config = get_performance_optimized_config()
        
        assert config.cpu == "2"
        assert config.memory == "4Gi"
        assert config.min_instances == 1
        assert config.max_instances == 20
        assert config.cpu_throttling == False
        assert config.bigquery_cache_ttl == 1800
    
    def test_deployment_config_generation(self):
        """Test deployment configuration generation."""
        config = CloudRunConfig()
        deployment_config = config.get_deployment_config()
        
        assert "apiVersion" in deployment_config
        assert deployment_config["kind"] == "Service"
        assert deployment_config["metadata"]["name"] == config.service_name
        assert "spec" in deployment_config
    
    def test_gcloud_deploy_command(self):
        """Test gcloud deployment command generation."""
        config = CloudRunConfig()
        command = config.get_gcloud_deploy_command()
        
        assert "gcloud run deploy" in command
        assert config.service_name in command
        assert config.region in command
        assert "--cpu" in command
        assert "--memory" in command

class TestUIDeploymentStatus:
    """Test UI deployment status monitoring."""
    
    def test_ui_deployment_status(self):
        """Test UI deployment status endpoint."""
        response = client.get("/api/debug/ui-deployment-status")
        assert response.status_code == 200
        
        data = response.json()
        assert "service_name" in data
        assert "status" in data
        assert "instances" in data
        assert "health" in data
        assert "performance" in data
        assert "cost_optimization" in data

class TestIntegration:
    """Integration tests for UI deployment optimization."""
    
    @patch('app.api.cost_monitoring.get_bigquery_usage_stats')
    def test_cost_monitoring_integration(self, mock_usage_stats):
        """Test cost monitoring integration."""
        mock_usage_stats.return_value = {
            "total_bytes": 2000000,
            "total_rows": 2000,
            "tables_count": 8,
            "estimated_cost": 0.01,
            "last_updated": datetime.now().isoformat()
        }
        
        # Test cost monitoring endpoint
        cost_response = client.get("/api/cost/current-usage")
        assert cost_response.status_code == 200
        
        data = cost_response.json()
        assert "current_usage" in data
        assert "optimization_score" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
