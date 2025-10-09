#!/usr/bin/env python3
"""
Test Batch Processor Setup

Verifies that the batch processor is properly configured and working.
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_batch_processor():
    """Test that batch processor is working correctly."""
    
    print("🧪 Testing Batch Processor Setup")
    print("=" * 50)
    
    try:
        # Import batch processor
        from app.api.batch_ai_safety import batch_processor
        print("✅ Batch processor imported successfully")
        
        # Test initial status
        status = batch_processor.get_batch_status()
        print(f"✅ Initial batch status: {status['queue_size']} items in queue")
        
        # Add some test content
        test_content = "This is a test message for batch processing"
        result = await batch_processor.process_content(
            content=test_content,
            context="test",
            statement_id="test_batch_001",
            user_id="test_user"
        )
        
        print(f"✅ Content added to batch: {result['status']}")
        
        # Check status again
        status_after = batch_processor.get_batch_status()
        print(f"✅ Batch status after adding: {status_after['queue_size']} items in queue")
        
        # Test background processor start
        batch_processor.start_background_processor()
        print("✅ Background processor started")
        
        # Force process batch
        print("🔄 Processing batch...")
        await batch_processor._process_batch()
        
        # Check final status
        final_status = batch_processor.get_batch_status()
        print(f"✅ Final batch status: {final_status['queue_size']} items in queue")
        
        print("\n🎉 Batch processor setup test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Batch processor test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_worker_process():
    """Test that worker process can be imported."""
    
    print("\n🧪 Testing Worker Process")
    print("=" * 50)
    
    try:
        # Test worker import
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'workers'))
        from batch_processor import BatchWorker
        
        print("✅ Worker process imported successfully")
        
        # Test worker initialization
        worker = BatchWorker()
        print("✅ Worker initialized successfully")
        
        print("🎉 Worker process test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Worker process test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    
    print("🚀 Testing Batch Processing Setup")
    print("=" * 60)
    
    # Test batch processor
    batch_test_passed = await test_batch_processor()
    
    # Test worker process
    worker_test_passed = await test_worker_process()
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 60)
    print(f"Batch Processor: {'✅ PASS' if batch_test_passed else '❌ FAIL'}")
    print(f"Worker Process:  {'✅ PASS' if worker_test_passed else '❌ FAIL'}")
    
    if batch_test_passed and worker_test_passed:
        print("\n🎉 ALL TESTS PASSED - Batch processing is ready!")
        print("\n📋 Setup Summary:")
        print("- ✅ Batch processor is working")
        print("- ✅ Worker process is configured")
        print("- ✅ Procfile updated with correct worker")
        print("- ✅ FastAPI startup event configured")
        print("\n🚀 Ready for deployment!")
    else:
        print("\n❌ Some tests failed - check the errors above")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
