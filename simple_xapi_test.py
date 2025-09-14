#!/usr/bin/env python3
"""
Simple xAPI Test - Test xAPI ingestion and Redis queuing

This script tests the xAPI ingestion flow without requiring the full worker setup.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any
import httpx
import redis

class SimpleXAPITest:
    """Simple xAPI test focusing on ingestion and Redis queuing."""
    
    def __init__(self, base_url: str = "https://taps-analytics-ui-245712978112.us-central1.run.app"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.redis_client = None
        
    async def setup(self):
        """Set up Redis connection."""
        print("🔧 Setting up Redis connection...")
        
        try:
            redis_url = "redis://localhost:6379"
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    def generate_test_statement(self) -> Dict[str, Any]:
        """Generate a simple test xAPI statement."""
        statement_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        return {
            "id": statement_id,
            "actor": {
                "objectType": "Agent",
                "mbox": "mailto:test@example.com",
                "name": "Test User"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"}
            },
            "object": {
                "id": "https://7taps.com/lesson/1",
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": "Test Lesson"},
                    "description": {"en-US": "A test lesson for end-to-end testing"}
                }
            },
            "timestamp": timestamp,
            "stored": timestamp,
            "context": {
                "platform": "7taps",
                "language": "en-US"
            },
            "result": {
                "completion": True,
                "success": True,
                "score": {"scaled": 0.9}
            }
        }
    
    async def send_xapi_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Send xAPI statement to the endpoint."""
        print(f"📤 Sending xAPI statement: {statement['id']}")
        
        # Use the 7taps webhook endpoint
        endpoint = f"{self.base_url}/statements"
        
        try:
            response = await self.client.post(
                endpoint,
                json=[statement],  # Send as array
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Basic N3RhcHNfdXNlcjo3dGFwc19wYXNzd29yZF8yMDI1"  # 7taps_user:7taps_password_2025 base64 encoded
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully sent statement: {result}")
                return result
            else:
                print(f"❌ Failed to send statement: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Error sending statement: {e}")
            return {"error": str(e)}
    
    async def check_redis_stream(self) -> List[Dict[str, Any]]:
        """Check Redis stream for new messages."""
        print("👀 Checking Redis stream...")
        
        stream_name = "xapi_statements"
        
        try:
            # Get current stream length
            stream_length = self.redis_client.xlen(stream_name)
            print(f"   Current stream length: {stream_length}")
            
            if stream_length > 0:
                # Read the last few messages
                messages = self.redis_client.xrevrange(
                    stream_name,
                    count=5,
                    max="+",
                    min="-"
                )
                
                print(f"   Found {len(messages)} recent messages")
                
                parsed_messages = []
                for message_id, fields in messages:
                    if 'data' in fields:
                        try:
                            data = json.loads(fields['data'])
                            parsed_messages.append({
                                "message_id": message_id,
                                "data": data,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                            print(f"   📨 Message: {message_id} - {data.get('id', 'no-id')}")
                        except json.JSONDecodeError as e:
                            print(f"   ⚠️ Failed to parse message {message_id}: {e}")
                
                return parsed_messages
            else:
                print("   No messages in stream")
                return []
                
        except Exception as e:
            print(f"❌ Error checking stream: {e}")
            return []
    
    async def test_xapi_ingestion(self):
        """Test the complete xAPI ingestion flow."""
        print("🚀 Starting Simple xAPI Test")
        print("=" * 40)
        
        await self.setup()
        
        # Generate test statement
        print("\n📝 Generating test statement...")
        test_statement = self.generate_test_statement()
        print(f"✅ Generated statement: {test_statement['id']}")
        
        # Check initial stream state
        print("\n👀 Checking initial Redis stream state...")
        initial_messages = await self.check_redis_stream()
        initial_count = len(initial_messages)
        
        # Send statement
        print("\n📤 Sending statement to endpoint...")
        send_result = await self.send_xapi_statement(test_statement)
        
        if "error" in send_result:
            print("❌ Failed to send statement, aborting test")
            return
        
        # Wait a moment for processing
        print("\n⏳ Waiting for processing...")
        await asyncio.sleep(2)
        
        # Check stream again
        print("\n👀 Checking Redis stream after sending...")
        final_messages = await self.check_redis_stream()
        final_count = len(final_messages)
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 TEST SUMMARY")
        print("=" * 40)
        print(f"📤 Statement sent: {test_statement['id']}")
        print(f"📨 Initial stream messages: {initial_count}")
        print(f"📨 Final stream messages: {final_count}")
        print(f"📈 New messages: {final_count - initial_count}")
        
        if final_count > initial_count:
            print("\n🎉 SUCCESS: xAPI statement was queued to Redis!")
            print("   xAPI statement → Redis Stream ✅")
            
            # Show the new message
            if final_messages:
                new_message = final_messages[0]
                print(f"\n📋 New message details:")
                print(f"   Message ID: {new_message['message_id']}")
                print(f"   Statement ID: {new_message['data'].get('id', 'N/A')}")
                print(f"   Actor: {new_message['data'].get('actor', {}).get('mbox', 'N/A')}")
                print(f"   Verb: {new_message['data'].get('verb', {}).get('id', 'N/A')}")
                print(f"   Object: {new_message['data'].get('object', {}).get('id', 'N/A')}")
        else:
            print("\n⚠️ ISSUE: No new messages in Redis stream")
            print("   Check endpoint logs and Redis configuration")
        
        await self.client.aclose()

async def main():
    """Main function to run the test."""
    test = SimpleXAPITest()
    await test.test_xapi_ingestion()

if __name__ == "__main__":
    asyncio.run(main())
