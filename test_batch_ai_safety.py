#!/usr/bin/env python3
"""
Test script for the improved batch AI safety system.

Tests the safety-first approach:
1. Obvious flags → Immediate AI analysis
2. Other content → Batch processing
"""

import asyncio
import json
from datetime import datetime

async def test_batch_ai_safety():
    """Test the batch AI safety system with various content types."""
    
    # Import the batch processor
    try:
        from app.api.batch_ai_safety import batch_processor
        print("✅ Batch AI safety module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import batch AI safety: {e}")
        return
    
    # Test cases
    test_cases = [
        {
            "content": "I want to kill myself because I can't stop using my phone",
            "context": "reflection",
            "expected": "immediate_ai",
            "description": "Critical obvious flag - should trigger immediate AI"
        },
        {
            "content": "I feel so depressed and hopeless about everything", 
            "context": "response",
            "expected": "immediate_ai",
            "description": "Medium obvious flag - should trigger immediate AI"
        },
        {
            "content": "I feel empty inside, like nothing matters anymore",
            "context": "reflection", 
            "expected": "immediate_ai",
            "description": "Medium obvious flag - should trigger immediate AI (matches local rules)"
        },
        {
            "content": "This lesson is challenging but I'm learning a lot",
            "context": "response",
            "expected": "batch_queue", 
            "description": "Normal content - should go to batch queue"
        },
        {
            "content": "This assignment is killing me with all the work",
            "context": "reflection",
            "expected": "batch_queue",
            "description": "Metaphorical expression - should go to batch queue"
        },
        {
            "content": "I'm struggling with focus and motivation lately",
            "context": "reflection",
            "expected": "batch_queue",
            "description": "Nuanced content - should go to batch queue (no obvious patterns)"
        }
    ]
    
    print(f"\n🧪 Testing {len(test_cases)} content samples...")
    print("=" * 60)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"Content: \"{test_case['content']}\"")
        print(f"Expected: {test_case['expected']}")
        
        try:
            # Process content through batch system
            result = await batch_processor.process_content(
                content=test_case['content'],
                context=test_case['context'],
                statement_id=f"test_{i}",
                user_id=f"testuser_{i}"
            )
            
            # Analyze result
            status = result.get('status', 'unknown')
            is_immediate = status == 'flagged' and result.get('analysis_metadata', {}).get('immediate_processing', False)
            is_queued = status == 'queued'
            
            if test_case['expected'] == 'immediate_ai':
                if status == 'flagged' and is_immediate:
                    print("✅ PASS - Immediate AI analysis triggered")
                else:
                    print(f"❌ FAIL - Expected immediate AI, got status: {status}")
            elif test_case['expected'] == 'batch_queue':
                if status == 'queued':
                    print("✅ PASS - Added to batch queue")
                else:
                    print(f"❌ FAIL - Expected batch queue, got status: {status}")
            
            results.append({
                "test_case": i,
                "description": test_case['description'],
                "expected": test_case['expected'],
                "actual_status": status,
                "result": result
            })
            
        except Exception as e:
            print(f"❌ ERROR - Test failed: {e}")
            results.append({
                "test_case": i,
                "description": test_case['description'],
                "expected": test_case['expected'],
                "error": str(e)
            })
    
    # Get batch status
    print(f"\n📊 Batch Status:")
    try:
        batch_status = batch_processor.get_batch_status()
        print(f"Queue size: {batch_status['queue_size']}")
        print(f"Last batch time: {batch_status['last_batch_time']}")
        print(f"Estimated tokens: {batch_status['estimated_tokens']}")
    except Exception as e:
        print(f"❌ Failed to get batch status: {e}")
    
    # Summary
    print(f"\n📋 Test Summary:")
    print("=" * 60)
    
    passed = sum(1 for r in results if 'error' not in r and 
                ((r['expected'] == 'immediate_ai' and r['actual_status'] == 'flagged') or
                 (r['expected'] == 'batch_queue' and r['actual_status'] == 'queued')))
    
    total = len(results)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("🎉 All tests passed! Batch AI safety system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the results above.")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"batch_ai_safety_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed
            },
            "results": results,
            "batch_status": batch_status if 'batch_status' in locals() else None
        }, f, indent=2)
    
    print(f"📄 Detailed results saved to: {results_file}")

if __name__ == "__main__":
    asyncio.run(test_batch_ai_safety())
