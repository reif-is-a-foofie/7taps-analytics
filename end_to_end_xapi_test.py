#!/usr/bin/env python3
"""
End-to-End xAPI Test Script

This script simulates real xAPI data flow:
1. Generates realistic xAPI statements
2. Sends them to the xAPI endpoint
3. Monitors worker processing
4. Verifies data appears in BigQuery
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx
import redis
from google.cloud import bigquery
from google.auth import default

class XAPITestDataGenerator:
    """Generate realistic xAPI test statements."""
    
    def __init__(self):
        self.lessons = [
            "https://7taps.com/lesson/1",
            "https://7taps.com/lesson/2", 
            "https://7taps.com/lesson/3",
            "https://7taps.com/lesson/4",
            "https://7taps.com/lesson/5"
        ]
        self.users = [
            "user1@example.com",
            "user2@example.com", 
            "user3@example.com",
            "user4@example.com",
            "user5@example.com"
        ]
        self.verbs = [
            {"id": "http://adlnet.gov/expapi/verbs/experienced", "display": {"en-US": "experienced"}},
            {"id": "http://adlnet.gov/expapi/verbs/completed", "display": {"en-US": "completed"}},
            {"id": "http://adlnet.gov/expapi/verbs/answered", "display": {"en-US": "answered"}},
            {"id": "http://adlnet.gov/expapi/verbs/attempted", "display": {"en-US": "attempted"}}
        ]
    
    def generate_statement(self, user: str = None, lesson: str = None, verb: str = None) -> Dict[str, Any]:
        """Generate a single xAPI statement."""
        if not user:
            user = self.users[0]
        if not lesson:
            lesson = self.lessons[0]
        if not verb:
            verb = self.verbs[0]
            
        statement_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        return {
            "id": statement_id,
            "actor": {
                "objectType": "Agent",
                "mbox": f"mailto:{user}",
                "name": user.split("@")[0]
            },
            "verb": verb,
            "object": {
                "id": lesson,
                "objectType": "Activity",
                "definition": {
                    "name": {"en-US": f"Lesson {lesson.split('/')[-1]}"},
                    "description": {"en-US": f"Interactive lesson content for {lesson.split('/')[-1]}"}
                }
            },
            "timestamp": timestamp,
            "stored": timestamp,
            "context": {
                "platform": "7taps",
                "language": "en-US",
                "extensions": {
                    "https://7taps.com/context/session": str(uuid.uuid4()),
                    "https://7taps.com/context/device": "mobile"
                }
            },
            "result": {
                "completion": True,
                "success": True,
                "score": {
                    "scaled": 0.85
                },
                "duration": "PT2M30S"
            }
        }
    
    def generate_lesson_completion_flow(self, user: str, lesson: str) -> List[Dict[str, Any]]:
        """Generate a complete lesson flow with multiple statements."""
        statements = []
        
        # 1. Lesson started
        statements.append(self.generate_statement(
            user=user,
            lesson=lesson,
            verb=self.verbs[3]  # attempted
        ))
        
        # 2. Lesson experienced (multiple interactions)
        for i in range(3):
            statements.append(self.generate_statement(
                user=user,
                lesson=lesson,
                verb=self.verbs[0]  # experienced
            ))
            time.sleep(0.1)  # Small delay between statements
        
        # 3. Questions answered
        for i in range(2):
            statements.append(self.generate_statement(
                user=user,
                lesson=lesson,
                verb=self.verbs[2]  # answered
            ))
            time.sleep(0.1)
        
        # 4. Lesson completed
        statements.append(self.generate_statement(
            user=user,
            lesson=lesson,
            verb=self.verbs[1]  # completed
        ))
        
        return statements

class XAPITestRunner:
    """Run end-to-end xAPI tests."""
    
    def __init__(self, base_url: str = "https://taps-analytics-ui-245712978112.us-central1.run.app"):
        self.base_url = base_url
        self.generator = XAPITestDataGenerator()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.redis_client = None
        self.bigquery_client = None
        
    async def setup(self):
        """Set up connections to Redis and BigQuery."""
        print("🔧 Setting up connections...")
        
        # Redis connection
        try:
            redis_url = "redis://localhost:6379"  # Local Redis for testing
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            print("   Continuing without Redis monitoring...")
        
        # BigQuery connection
        try:
            credentials, project = default()
            self.bigquery_client = bigquery.Client(credentials=credentials, project=project)
            print("✅ BigQuery connection established")
        except Exception as e:
            print(f"❌ BigQuery connection failed: {e}")
            raise
    
    async def send_xapi_statements(self, statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send xAPI statements to the endpoint."""
        print(f"📤 Sending {len(statements)} xAPI statements...")
        
        # Use the 7taps webhook endpoint
        endpoint = f"{self.base_url}/api/7taps/statements"
        
        try:
            response = await self.client.post(
                endpoint,
                json=statements,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Basic dGVzdDp0ZXN0"  # test:test base64 encoded
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully sent statements: {result}")
                return result
            else:
                print(f"❌ Failed to send statements: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Error sending statements: {e}")
            return {"error": str(e)}
    
    async def monitor_redis_stream(self, duration_seconds: int = 30) -> List[Dict[str, Any]]:
        """Monitor Redis stream for new messages."""
        if not self.redis_client:
            print("⚠️ Redis not available, skipping stream monitoring")
            return []
        
        print(f"👀 Monitoring Redis stream for {duration_seconds} seconds...")
        
        stream_name = "xapi_statements"
        messages = []
        start_time = time.time()
        
        try:
            # Get initial stream length
            initial_length = self.redis_client.xlen(stream_name)
            print(f"   Initial stream length: {initial_length}")
            
            # Monitor for new messages
            while time.time() - start_time < duration_seconds:
                current_length = self.redis_client.xlen(stream_name)
                if current_length > initial_length:
                    # Read new messages
                    new_messages = self.redis_client.xrange(
                        stream_name,
                        min=f"{initial_length}-0",
                        max="+"
                    )
                    
                    for message_id, fields in new_messages:
                        if 'data' in fields:
                            try:
                                data = json.loads(fields['data'])
                                messages.append({
                                    "message_id": message_id,
                                    "data": data,
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                print(f"   📨 New message: {message_id}")
                            except json.JSONDecodeError as e:
                                print(f"   ⚠️ Failed to parse message {message_id}: {e}")
                    
                    initial_length = current_length
                
                await asyncio.sleep(1)
            
            print(f"✅ Stream monitoring complete. Found {len(messages)} new messages")
            return messages
            
        except Exception as e:
            print(f"❌ Error monitoring stream: {e}")
            return []
    
    async def check_bigquery_data(self, expected_statements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if data appears in BigQuery."""
        print("🔍 Checking BigQuery for new data...")
        
        try:
            # Query the user_activities table
            query = """
            SELECT 
                statement_id,
                actor_mbox,
                verb_id,
                object_id,
                timestamp,
                result_completion,
                result_success
            FROM `taps-data.taps_data.user_activities`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)
            ORDER BY timestamp DESC
            LIMIT 100
            """
            
            query_job = self.bigquery_client.query(query)
            results = list(query_job.result())
            
            print(f"✅ Found {len(results)} recent records in BigQuery")
            
            # Check if our test statements are present
            found_statements = []
            for row in results:
                for stmt in expected_statements:
                    if (row.statement_id == stmt["id"] or 
                        row.actor_mbox == stmt["actor"]["mbox"]):
                        found_statements.append({
                            "statement_id": row.statement_id,
                            "actor": row.actor_mbox,
                            "verb": row.verb_id,
                            "object": row.object_id,
                            "timestamp": str(row.timestamp),
                            "completion": row.result_completion,
                            "success": row.result_success
                        })
            
            print(f"✅ Found {len(found_statements)} matching test statements")
            
            return {
                "total_recent_records": len(results),
                "matching_test_statements": len(found_statements),
                "found_statements": found_statements,
                "all_recent_records": [
                    {
                        "statement_id": row.statement_id,
                        "actor": row.actor_mbox,
                        "verb": row.verb_id,
                        "object": row.object_id,
                        "timestamp": str(row.timestamp)
                    } for row in results[:10]  # Show first 10
                ]
            }
            
        except Exception as e:
            print(f"❌ Error checking BigQuery: {e}")
            return {"error": str(e)}
    
    async def run_end_to_end_test(self):
        """Run the complete end-to-end test."""
        print("🚀 Starting End-to-End xAPI Test")
        print("=" * 50)
        
        await self.setup()
        
        # Generate test data
        print("\n📝 Generating test data...")
        test_statements = []
        
        # Generate statements for different users and lessons
        for i, user in enumerate(self.generator.users[:3]):  # Test with 3 users
            lesson = self.generator.lessons[i % len(self.generator.lessons)]
            statements = self.generator.generate_lesson_completion_flow(user, lesson)
            test_statements.extend(statements)
        
        print(f"✅ Generated {len(test_statements)} test statements")
        
        # Send statements
        print("\n📤 Sending statements to endpoint...")
        send_result = await self.send_xapi_statements(test_statements)
        
        if "error" in send_result:
            print("❌ Failed to send statements, aborting test")
            return
        
        # Monitor Redis stream
        print("\n👀 Monitoring Redis stream...")
        stream_messages = await self.monitor_redis_stream(duration_seconds=30)
        
        # Wait a bit for processing
        print("\n⏳ Waiting for worker processing...")
        await asyncio.sleep(10)
        
        # Check BigQuery
        print("\n🔍 Checking BigQuery...")
        bigquery_result = await self.check_bigquery_data(test_statements)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 END-TO-END TEST SUMMARY")
        print("=" * 50)
        print(f"📤 Statements sent: {len(test_statements)}")
        print(f"📨 Redis messages: {len(stream_messages)}")
        print(f"🗄️ BigQuery records: {bigquery_result.get('total_recent_records', 0)}")
        print(f"✅ Matching statements: {bigquery_result.get('matching_test_statements', 0)}")
        
        if bigquery_result.get('matching_test_statements', 0) > 0:
            print("\n🎉 SUCCESS: End-to-end flow is working!")
            print("   xAPI statements → Redis → Worker → BigQuery")
        else:
            print("\n⚠️ PARTIAL SUCCESS: Data flow may have issues")
            print("   Check worker logs and BigQuery configuration")
        
        # Show sample data
        if bigquery_result.get('found_statements'):
            print("\n📋 Sample processed statements:")
            for stmt in bigquery_result['found_statements'][:3]:
                print(f"   - {stmt['actor']} {stmt['verb'].split('/')[-1]} {stmt['object'].split('/')[-1]}")
        
        await self.client.aclose()

async def main():
    """Main function to run the test."""
    runner = XAPITestRunner()
    await runner.run_end_to_end_test()

if __name__ == "__main__":
    asyncio.run(main())

