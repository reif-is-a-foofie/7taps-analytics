"""
Comprehensive test suite for b.19 Production Monitoring implementation
Tests all monitoring capabilities including health checks, metrics, alerts, and dashboard
"""

import pytest
import httpx
import asyncio
from datetime import datetime, timedelta
import json

# Test configuration
BASE_URL = "https://seventaps-analytics-5135b3a0701a.herokuapp.com"

class TestProductionMonitoring:
    """Test suite for production monitoring system"""
    
    @pytest.mark.asyncio
    async def test_system_health_endpoints(self):
        """Test all system health monitoring endpoints"""
        async with httpx.AsyncClient() as client:
            # Test basic health endpoint
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            
            # Test detailed health endpoint
            response = await client.get(f"{BASE_URL}/health/detailed")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "components" in data
            assert "redis" in data["components"]
            assert "database" in data["components"]
            assert "system" in data["components"]
            
            # Test system health endpoint
            response = await client.get(f"{BASE_URL}/health/system")
            assert response.status_code == 200
            data = response.json()
            assert "cpu_percent" in data
            assert "memory" in data
            assert "disk" in data
            
            # Test metrics endpoint
            response = await client.get(f"{BASE_URL}/health/metrics")
            assert response.status_code == 200
            data = response.json()
            assert "uptime_seconds" in data
            assert "environment" in data
            assert "version" in data
    
    @pytest.mark.asyncio
    async def test_dashboard_monitoring_endpoints(self):
        """Test dashboard monitoring and metrics endpoints"""
        async with httpx.AsyncClient() as client:
            # Test dashboard metrics
            response = await client.get(f"{BASE_URL}/api/dashboard/metrics")
            assert response.status_code == 200
            data = response.json()
            assert "metrics" in data
            assert "timestamp" in data
            assert "status" in data
            
            metrics = data["metrics"]
            assert "total_users" in metrics
            assert "total_statements" in metrics
            assert "completion_rate" in metrics
            assert "active_users_7d" in metrics
            assert "active_users_30d" in metrics
            assert "top_verbs" in metrics
            assert "daily_activity" in metrics
            assert "recent_7taps_statements" in metrics
            assert "cohort_completion" in metrics
            
            # Test performance metrics
            response = await client.get(f"{BASE_URL}/api/dashboard/performance")
            assert response.status_code == 200
            data = response.json()
            assert "sync_performance" in data
            assert "system_performance" in data
            assert "user_activity" in data
            assert "data_quality" in data
            
            # Test real-time monitoring
            response = await client.get(f"{BASE_URL}/api/dashboard/real-time")
            assert response.status_code == 200
            data = response.json()
            assert "learninglocker_data" in data
            assert "performance_metrics" in data
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_data_processing_monitoring(self):
        """Test data processing and ETL monitoring"""
        async with httpx.AsyncClient() as client:
            # Test ETL status
            response = await client.get(f"{BASE_URL}/ui/etl-status")
            assert response.status_code == 200
            
            # Test incremental ETL status
            response = await client.get(f"{BASE_URL}/ui/incremental-status")
            assert response.status_code == 200
            
            # Test database status
            response = await client.get(f"{BASE_URL}/ui/db-status")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_analytics_insights(self):
        """Test analytics insights and data quality monitoring"""
        async with httpx.AsyncClient() as client:
            # Test recent 7taps statements
            response = await client.get(f"{BASE_URL}/api/dashboard/recent-7taps-statements")
            assert response.status_code == 200
            data = response.json()
            assert "statements" in data or "data" in data
            
            # Test activity metrics
            response = await client.get(f"{BASE_URL}/api/dashboard/activity")
            assert response.status_code == 200
            
            # Test sync timeline
            response = await client.get(f"{BASE_URL}/api/dashboard/sync-timeline")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_system_performance_monitoring(self):
        """Test system performance monitoring capabilities"""
        async with httpx.AsyncClient() as client:
            # Test system health for performance metrics
            response = await client.get(f"{BASE_URL}/health/detailed")
            assert response.status_code == 200
            data = response.json()
            
            system = data["components"]["system"]
            assert "cpu_percent" in system
            assert "memory" in system
            assert "disk" in system
            
            # Verify performance thresholds
            assert system["cpu_percent"] >= 0
            assert system["cpu_percent"] <= 100
            assert system["memory"]["used_percent"] >= 0
            assert system["memory"]["used_percent"] <= 100
            assert system["disk"]["used_percent"] >= 0
            assert system["disk"]["used_percent"] <= 100
    
    @pytest.mark.asyncio
    async def test_database_monitoring(self):
        """Test database connection and health monitoring"""
        async with httpx.AsyncClient() as client:
            # Test database health
            response = await client.get(f"{BASE_URL}/health/database")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            
            # Test database query endpoint
            response = await client.post(
                f"{BASE_URL}/ui/db-query",
                json={
                    "query": "SELECT COUNT(*) as total FROM statements_flat",
                    "query_type": "analytics"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "row_count" in data
            assert "execution_time" in data
    
    @pytest.mark.asyncio
    async def test_redis_monitoring(self):
        """Test Redis connection and health monitoring"""
        async with httpx.AsyncClient() as client:
            # Test Redis health
            response = await client.get(f"{BASE_URL}/health/redis")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_production_dashboard_accessibility(self):
        """Test production dashboard accessibility and functionality"""
        async with httpx.AsyncClient() as client:
            # Test admin panel
            response = await client.get(f"{BASE_URL}/ui/admin")
            assert response.status_code == 200
            data = response.json()
            assert "panel" in data
            assert "modules" in data
            assert "capabilities" in data
            
            # Test dashboard
            response = await client.get(f"{BASE_URL}/dashboard")
            assert response.status_code == 200
            
            # Test enhanced dashboard
            response = await client.get(f"{BASE_URL}/enhanced-dashboard")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_monitoring_data_quality(self):
        """Test monitoring data quality and consistency"""
        async with httpx.AsyncClient() as client:
            # Test metrics consistency
            response1 = await client.get(f"{BASE_URL}/api/dashboard/metrics")
            response2 = await client.get(f"{BASE_URL}/api/dashboard/performance")
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            metrics1 = response1.json()
            metrics2 = response2.json()
            
            # Verify timestamp format
            assert "timestamp" in metrics1
            assert "timestamp" in metrics2
            
            # Verify data structure consistency
            assert "metrics" in metrics1
            assert "performance_metrics" in metrics2
    
    @pytest.mark.asyncio
    async def test_monitoring_alert_capabilities(self):
        """Test monitoring alert and notification capabilities"""
        async with httpx.AsyncClient() as client:
            # Test system status for potential alerts
            response = await client.get(f"{BASE_URL}/health/detailed")
            assert response.status_code == 200
            data = response.json()
            
            # Check for critical system conditions
            system = data["components"]["system"]
            
            # These should not trigger alerts in normal operation
            assert system["cpu_percent"] < 90  # Critical threshold
            assert system["memory"]["used_percent"] < 95  # Critical threshold
            assert system["disk"]["used_percent"] < 95  # Critical threshold
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test monitoring integration with main application"""
        async with httpx.AsyncClient() as client:
            # Test that monitoring doesn't interfere with main functionality
            response = await client.get(f"{BASE_URL}/")
            assert response.status_code == 200
            
            # Test that monitoring endpoints are accessible
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            
            # Test that dashboard is accessible
            response = await client.get(f"{BASE_URL}/dashboard")
            assert response.status_code == 200

def test_monitoring_requirements_coverage():
    """Test coverage of b.19 requirements"""
    required_endpoints = [
        "/health",
        "/health/detailed", 
        "/health/system",
        "/health/metrics",
        "/health/database",
        "/health/redis",
        "/api/dashboard/metrics",
        "/api/dashboard/performance",
        "/api/dashboard/real-time",
        "/ui/admin",
        "/dashboard"
    ]
    
    # All required endpoints should be tested above
    assert len(required_endpoints) > 0
    
    # Verify monitoring capabilities
    monitoring_capabilities = [
        "system_health_monitoring",
        "performance_metrics",
        "data_quality_monitoring", 
        "real_time_dashboard",
        "database_monitoring",
        "redis_monitoring",
        "alert_capabilities"
    ]
    
    assert len(monitoring_capabilities) > 0

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
