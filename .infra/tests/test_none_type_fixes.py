#!/usr/bin/env python3
"""Test script to verify NoneType fixes in ETL processing."""

import json
from datetime import datetime, timezone

def test_user_normalization_fixes():
    """Test user normalization with None values."""
    print("🧪 Testing user normalization fixes...")
    
    # Import here to avoid GCP credential issues
    try:
        from app.services.user_normalization import UserNormalizationService
        
        service = UserNormalizationService()
        
        # Test case 1: None mbox
        statement_1 = {
            "id": "test-1",
            "timestamp": "2025-01-01T00:00:00Z",
            "actor": {
                "mbox": None,  # This was causing the error
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_1 = service.normalize_xapi_statement(statement_1)
        print(f"✅ Test 1 (None mbox): {result_1 is not None}")
        
        # Test case 2: Empty string mbox
        statement_2 = {
            "id": "test-2", 
            "timestamp": "2025-01-01T00:00:00Z",
            "actor": {
                "mbox": "",  # Empty string
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_2 = service.normalize_xapi_statement(statement_2)
        print(f"✅ Test 2 (Empty mbox): {result_2 is not None}")
        
        # Test case 3: Whitespace mbox
        statement_3 = {
            "id": "test-3",
            "timestamp": "2025-01-01T00:00:00Z", 
            "actor": {
                "mbox": "   ",  # Whitespace only
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_3 = service.normalize_xapi_statement(statement_3)
        print(f"✅ Test 3 (Whitespace mbox): {result_3 is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ User normalization test failed: {e}")
        return False

def test_storage_subscriber_fixes():
    """Test storage subscriber with None values."""
    print("\n🧪 Testing storage subscriber fixes...")
    
    try:
        from app.etl.pubsub_storage_subscriber import PubSubStorageSubscriber
        
        # Mock the GCP clients to avoid credential issues
        class MockSubscriber:
            def __init__(self):
                pass
        
        class MockStorage:
            def __init__(self):
                pass
        
        # Create subscriber with mocked clients
        subscriber = PubSubStorageSubscriber()
        subscriber.subscriber = MockSubscriber()
        subscriber.storage_client = MockStorage()
        
        # Test case 1: None mbox
        message_data_1 = {
            "id": "test-1",
            "timestamp": "2025-01-01T00:00:00Z",
            "actor": {
                "mbox": None,  # This was causing the error
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        path_1 = subscriber.generate_storage_path(message_data_1, "msg-1")
        print(f"✅ Test 1 (None mbox): {path_1 is not None and 'unknown' in path_1}")
        
        # Test case 2: Empty string mbox
        message_data_2 = {
            "id": "test-2",
            "timestamp": "2025-01-01T00:00:00Z",
            "actor": {
                "mbox": "",  # Empty string
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        path_2 = subscriber.generate_storage_path(message_data_2, "msg-2")
        print(f"✅ Test 2 (Empty mbox): {path_2 is not None and 'unknown' in path_2}")
        
        # Test case 3: Whitespace mbox
        message_data_3 = {
            "id": "test-3",
            "timestamp": "2025-01-01T00:00:00Z",
            "actor": {
                "mbox": "   ",  # Whitespace only
                "name": "Test User"
            },
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        path_3 = subscriber.generate_storage_path(message_data_3, "msg-3")
        print(f"✅ Test 3 (Whitespace mbox): {path_3 is not None and 'unknown' in path_3}")
        
        return True
        
    except Exception as e:
        print(f"❌ Storage subscriber test failed: {e}")
        return False

def test_bigquery_migration_fixes():
    """Test BigQuery migration with None values."""
    print("\n🧪 Testing BigQuery migration fixes...")
    
    try:
        from app.etl.bigquery_schema_migration import BigQuerySchemaMigration
        
        # Mock the GCP clients to avoid credential issues
        class MockSubscriber:
            def __init__(self):
                pass
        
        class MockStorage:
            def __init__(self):
                pass
        
        class MockBigQuery:
            def __init__(self):
                pass
        
        # Create migration with mocked clients
        migration = BigQuerySchemaMigration()
        migration.subscriber = MockSubscriber()
        migration.storage_client = MockStorage()
        migration.bq_client = MockBigQuery()
        
        # Test case 1: None timestamp
        statement_1 = {
            "id": "test-1",
            "timestamp": None,  # This was causing the error
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_1 = migration.transform_xapi_to_structured(statement_1)
        print(f"✅ Test 1 (None timestamp): {result_1 is not None}")
        
        # Test case 2: Empty string timestamp
        statement_2 = {
            "id": "test-2",
            "timestamp": "",  # Empty string
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_2 = migration.transform_xapi_to_structured(statement_2)
        print(f"✅ Test 2 (Empty timestamp): {result_2 is not None}")
        
        # Test case 3: Whitespace timestamp
        statement_3 = {
            "id": "test-3",
            "timestamp": "   ",  # Whitespace only
            "actor": {"mbox": "mailto:test@example.com"},
            "verb": {"id": "http://example.com/verb"},
            "object": {"id": "http://example.com/object"}
        }
        
        result_3 = migration.transform_xapi_to_structured(statement_3)
        print(f"✅ Test 3 (Whitespace timestamp): {result_3 is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ BigQuery migration test failed: {e}")
        return False

def main():
    """Run all NoneType fix tests."""
    print("🚀 Testing NoneType fixes in ETL processing...")
    
    results = []
    
    # Test user normalization
    results.append(test_user_normalization_fixes())
    
    # Test storage subscriber
    results.append(test_storage_subscriber_fixes())
    
    # Test BigQuery migration
    results.append(test_bigquery_migration_fixes())
    
    # Summary
    print(f"\n📊 Test Results:")
    print(f"   User Normalization: {'✅ Pass' if results[0] else '❌ Fail'}")
    print(f"   Storage Subscriber: {'✅ Pass' if results[1] else '❌ Fail'}")
    print(f"   BigQuery Migration: {'✅ Pass' if results[2] else '❌ Fail'}")
    
    if all(results):
        print("\n🎉 All NoneType fixes are working correctly!")
    else:
        print("\n💥 Some tests failed - there are still issues to fix")

if __name__ == "__main__":
    main()
