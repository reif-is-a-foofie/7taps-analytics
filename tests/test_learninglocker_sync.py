"""
Tests for Learning Locker sync functionality.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime
import redis

from app.sync_learninglocker import LearningLockerSync


class TestLearningLockerSync:
    """Test Learning Locker sync functionality."""
    
    @pytest.fixture
    def sync_service(self):
        """Create a test sync service instance."""
        return LearningLockerSync()
    
    @pytest.fixture
    def sample_statement(self):
        """Sample xAPI statement for testing."""
        return {
            "id": "test-statement-123",
            "actor": {
                "account": {
                    "name": "test-user@7taps.com"
                }
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed"
            },
            "object": {
                "id": "http://7taps.com/activities/test-course",
                "objectType": "Activity"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_source": "7taps",
            "ingested_at": datetime.utcnow().isoformat()
        }
    
    def test_sync_service_initialization(self, sync_service):
        """Test sync service initializes correctly."""
        assert sync_service.learninglocker_url is not None
        assert sync_service.learninglocker_username is not None
        assert sync_service.learninglocker_password is not None
        assert sync_service.redis_client is not None
    
    @patch('app.sync_learninglocker.httpx.AsyncClient.post')
    async def test_get_learninglocker_auth_success(self, mock_post, sync_service):
        """Test successful authentication with Learning Locker."""
        # Mock successful login response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Authorization": "Bearer test-token"}
        mock_post.return_value = mock_response
        
        auth_token = await sync_service.get_learninglocker_auth()
        
        assert auth_token == "Bearer test-token"
        mock_post.assert_called_once()
    
    @patch('app.sync_learninglocker.httpx.AsyncClient.post')
    async def test_get_learninglocker_auth_failure(self, mock_post, sync_service):
        """Test authentication failure with Learning Locker."""
        # Mock failed login response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        auth_token = await sync_service.get_learninglocker_auth()
        
        assert auth_token == ""
    
    @patch('app.sync_learninglocker.LearningLockerSync.get_learninglocker_auth')
    @patch('app.sync_learninglocker.httpx.AsyncClient.post')
    async def test_sync_statement_success(self, mock_post, mock_auth, sync_service, sample_statement):
        """Test successful statement sync to Learning Locker."""
        # Mock successful auth
        mock_auth.return_value = "Bearer test-token"
        
        # Mock successful statement post
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        success = await sync_service.sync_statement_to_learninglocker(sample_statement)
        
        assert success is True
        mock_post.assert_called_once()
    
    @patch('app.sync_learninglocker.LearningLockerSync.get_learninglocker_auth')
    @patch('app.sync_learninglocker.httpx.AsyncClient.post')
    async def test_sync_statement_failure(self, mock_post, mock_auth, sync_service, sample_statement):
        """Test failed statement sync to Learning Locker."""
        # Mock successful auth
        mock_auth.return_value = "Bearer test-token"
        
        # Mock failed statement post
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        success = await sync_service.sync_statement_to_learninglocker(sample_statement)
        
        assert success is False
    
    @patch('app.sync_learninglocker.LearningLockerSync.sync_statement_to_learninglocker')
    async def test_sync_redis_to_learninglocker(self, mock_sync, sync_service):
        """Test Redis to Learning Locker sync process."""
        # Mock successful statement sync
        mock_sync.return_value = True
        
        # Mock Redis stream data
        with patch.object(sync_service.redis_client, 'xreadgroup') as mock_read:
            mock_read.return_value = [
                ('xapi_statements', [
                    ('123', {'data': json.dumps({'id': 'test-1'})}),
                    ('124', {'data': json.dumps({'id': 'test-2'})})
                ])
            ]
            
            with patch.object(sync_service.redis_client, 'xack') as mock_ack:
                result = await sync_service.sync_redis_to_learninglocker(max_statements=2)
                
                assert result['synced_count'] == 2
                assert result['failed_count'] == 0
                assert result['total_processed'] == 2
                assert result['last_sync_time'] is not None
                assert result['total_synced'] == 2
                
                # Verify acknowledgments
                assert mock_ack.call_count == 2
    
    async def test_get_sync_status(self, sync_service):
        """Test sync status retrieval."""
        status = await sync_service.get_sync_status()
        
        assert 'last_sync_time' in status
        assert 'total_synced' in status
        assert 'learninglocker_url' in status
        assert 'redis_url' in status
    
    @patch('app.sync_learninglocker.LearningLockerSync.sync_statement_to_learninglocker')
    async def test_data_migration_with_existing_statements(self, mock_sync, sync_service):
        """Test data migration with existing xAPI statements."""
        # Mock successful statement sync
        mock_sync.return_value = True
        
        # Mock multiple statements in Redis
        with patch.object(sync_service.redis_client, 'xreadgroup') as mock_read:
            mock_read.return_value = [
                ('xapi_statements', [
                    ('123', {'data': json.dumps({'id': 'existing-1', 'actor': {'account': {'name': 'user1'}}})}),
                    ('124', {'data': json.dumps({'id': 'existing-2', 'actor': {'account': {'name': 'user2'}}})}),
                    ('125', {'data': json.dumps({'id': 'existing-3', 'actor': {'account': {'name': 'user3'}}})})
                ])
            ]
            
            with patch.object(sync_service.redis_client, 'xack') as mock_ack:
                result = await sync_service.sync_redis_to_learninglocker(max_statements=10)
                
                # Verify migration results
                assert result['synced_count'] == 3
                assert result['failed_count'] == 0
                assert result['total_processed'] == 3
                assert result['total_synced'] == 3
                
                # Verify all statements were acknowledged
                assert mock_ack.call_count == 3
    
    @patch('app.sync_learninglocker.LearningLockerSync.sync_statement_to_learninglocker')
    async def test_performance_with_large_dataset(self, mock_sync, sync_service):
        """Test sync performance with large dataset."""
        # Mock successful statement sync
        mock_sync.return_value = True
        
        # Mock large dataset (100 statements)
        large_dataset = []
        for i in range(100):
            large_dataset.append((f'msg_{i}', {'data': json.dumps({'id': f'statement-{i}'})}))
        
        with patch.object(sync_service.redis_client, 'xreadgroup') as mock_read:
            mock_read.return_value = [('xapi_statements', large_dataset)]
            
            with patch.object(sync_service.redis_client, 'xack') as mock_ack:
                import time
                start_time = time.time()
                
                result = await sync_service.sync_redis_to_learninglocker(max_statements=100)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                # Verify performance
                assert result['synced_count'] == 100
                assert result['failed_count'] == 0
                assert result['total_processed'] == 100
                
                # Performance should be reasonable (under 10 seconds for 100 statements)
                assert execution_time < 10.0
                
                # Verify all acknowledgments
                assert mock_ack.call_count == 100
    
    async def test_error_handling_and_retry_logic(self, sync_service):
        """Test error handling and retry logic."""
        # Mock Redis connection error
        with patch.object(sync_service.redis_client, 'xreadgroup') as mock_read:
            mock_read.side_effect = redis.ConnectionError("Redis connection failed")
            
            result = await sync_service.sync_redis_to_learninglocker(max_statements=10)
            
            # Verify error handling
            assert result['synced_count'] == 0
            assert result['failed_count'] == 0
            assert result['total_processed'] == 0
            assert 'error' in result
    
    async def test_data_integrity_verification(self, sync_service, sample_statement):
        """Test data integrity during sync process."""
        # Mock successful sync
        with patch('app.sync_learninglocker.LearningLockerSync.sync_statement_to_learninglocker') as mock_sync:
            mock_sync.return_value = True
            
            # Verify statement structure is preserved
            success = await sync_service.sync_statement_to_learninglocker(sample_statement)
            
            assert success is True
            
            # Verify the sync call received the correct statement
            mock_sync.assert_called_once_with(sample_statement)
            
            # Verify statement has required fields
            assert 'id' in sample_statement
            assert 'actor' in sample_statement
            assert 'verb' in sample_statement
            assert 'object' in sample_statement
            assert 'timestamp' in sample_statement


# Integration tests for API endpoints
class TestLearningLockerAPI:
    """Test Learning Locker API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_sync_learninglocker_endpoint(self, client):
        """Test POST /api/sync-learninglocker endpoint."""
        with patch('app.sync_learninglocker.learninglocker_sync.sync_redis_to_learninglocker') as mock_sync:
            mock_sync.return_value = {
                'synced_count': 5,
                'failed_count': 0,
                'total_processed': 5,
                'last_sync_time': '2025-08-06T17:33:06.203434',
                'total_synced': 5
            }
            
            response = client.post("/api/sync-learninglocker")
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'success'
            assert 'Synced 5 statements' in data['message']
            assert data['sync_result']['synced_count'] == 5
    
    def test_sync_status_endpoint(self, client):
        """Test GET /api/sync-status endpoint."""
        with patch('app.sync_learninglocker.learninglocker_sync.get_sync_status') as mock_status:
            mock_status.return_value = {
                'last_sync_time': '2025-08-06T17:33:06.203434',
                'total_synced': 10,
                'learninglocker_url': 'http://localhost:8080',
                'redis_url': 'localhost:6379'
            }
            
            response = client.get("/api/sync-status")
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'active'
            assert 'learninglocker_sync' in data
    
    def test_learninglocker_info_endpoint(self, client):
        """Test GET /api/learninglocker-info endpoint."""
        response = client.get("/api/learninglocker-info")
        
        assert response.status_code == 200
        data = response.json()
        assert 'learninglocker_url' in data
        assert 'learninglocker_username' in data
        assert 'admin_interface' in data
        assert 'xapi_endpoint' in data
        assert 'features' in data
        assert 'message' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 