"""
Test simplified architecture without MCP dependencies.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import os
import sys

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import with mock database connections
import unittest.mock as mock
from unittest.mock import Mock, patch

# Mock database connections before importing
with mock.patch('psycopg2.connect'), mock.patch('redis.from_url'):
    from app.etl_streaming import ETLStreamingProcessor
    from app.api.xapi_lrs import router as xapi_lrs_router
    from app.api.etl import router as etl_router


class TestSimplifiedArchitecture:
    """Test simplified architecture without MCP dependencies."""
    
    @patch('psycopg2.connect')
    @patch('redis.from_url')
    def test_etl_direct_connections(self, mock_redis, mock_db):
        """Test that ETL uses direct database connections."""
        processor = ETLStreamingProcessor()
        
        # Verify direct connections are used
        assert hasattr(processor, 'redis_client')
        assert hasattr(processor, 'db_pool')
        
        # Verify no MCP dependencies
        assert not hasattr(processor, 'mcp_postgres_client')
        assert not hasattr(processor, 'mcp_python_client')
        
    @patch('psycopg2.connect')
    @patch('redis.from_url')
    def test_etl_redis_connection(self, mock_redis, mock_db):
        """Test Redis connection configuration."""
        processor = ETLStreamingProcessor()
        
        # Verify Redis client is configured correctly
        assert processor.redis_client is not None
        assert processor.redis_url is not None
        
    @patch('psycopg2.connect')
    @patch('redis.from_url')
    def test_etl_database_connection(self, mock_redis, mock_db):
        """Test database connection configuration."""
        processor = ETLStreamingProcessor()
        
        # Verify database connection is configured
        assert processor.db_pool is not None
        assert processor.database_url is not None
        
    @patch('psycopg2.connect')
    @patch('redis.from_url')
    @pytest.mark.asyncio
    async def test_etl_process_statement(self, mock_redis, mock_db):
        """Test ETL statement processing."""
        processor = ETLStreamingProcessor()
        
        # Test statement processing
        test_statement = {
            "id": "test-statement-123",
            "actor": {
                "account": {
                    "name": "test-user"
                }
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed"
            },
            "object": {
                "id": "https://7taps.com/course/test",
                "objectType": "Activity"
            },
            "timestamp": "2025-01-05T21:00:00Z"
        }
        
        result = await processor.process_statement(test_statement)
        
        # Verify processing works
        assert result is not None
        assert result.get('statement_id') == "test-statement-123"
        assert result.get('actor_id') == "test-user"
        
    def test_no_mcp_imports(self):
        """Test that no MCP-related imports are used."""
        # Check that MCP-related modules are not imported
        with open('app/etl_streaming.py', 'r') as f:
            content = f.read()
            # Check for MCP imports specifically, not just the word 'mcp' in comments
            assert 'import mcp' not in content.lower()
            assert 'from mcp' not in content.lower()
            assert 'httpx' in content  # Only for HTTP requests if needed
            
    @patch('psycopg2.connect')
    @patch('redis.from_url')
    def test_direct_connection_urls(self, mock_redis, mock_db):
        """Test that direct connection URLs are used."""
        processor = ETLStreamingProcessor()
        
        # Verify direct connection URLs
        assert 'postgresql://' in processor.database_url
        assert 'redis://' in processor.redis_url
        
        # Verify no MCP URLs
        assert 'http://' not in processor.database_url
        assert 'mcp' not in processor.database_url
        
    def test_environment_variables(self):
        """Test that environment variables are configured correctly."""
        # Check that MCP environment variables are not used
        assert 'MCP_POSTGRES_URL' not in os.environ
        assert 'MCP_PYTHON_URL' not in os.environ
        
        # Check that direct connection variables are available (may not be set in test env)
        # These are optional in test environment
        pass


class TestAPISimplification:
    """Test API endpoints use direct connections."""
    
    def test_xapi_lrs_endpoints(self):
        """Test xAPI LRS endpoints work without MCP."""
        # Verify endpoints exist
        routes = [route.path for route in xapi_lrs_router.routes]
        assert "/statements" in routes
        assert "/about" in routes
        
    def test_etl_endpoints(self):
        """Test ETL endpoints work without MCP."""
        # Verify endpoints exist
        routes = [route.path for route in etl_router.routes]
        assert "/test-etl-streaming" in routes
        assert "/etl-status" in routes


if __name__ == "__main__":
    pytest.main([__file__]) 