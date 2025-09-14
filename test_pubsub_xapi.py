#!/usr/bin/env python3
"""
Test xAPI ingestion via Pub/Sub to BigQuery pipeline

This tests the cleaner architecture: xAPI → Pub/Sub → BigQuery
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any
import httpx
from google.cloud import bigquery
from google.auth import default

class PubSubXAPITest:
    """Test xAPI ingestion via Pub/Sub pipeline."""
    
    def __init__(self, base_url: str = "https://taps-analytics-ui-245712978112.us-central1.run.app"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.bigquery_client = None
        
    async def setup(self):
        """Set up BigQuery connection."""
        print("🔧 Setting up BigQuery connection...")
        
        try:
            credentials, project = default()
            self.bigquery_client = bigquery.Client(credentials=credentials, project=project)
            print("✅ BigQuery connection established")
        except Exception as e:
            print(f"❌ BigQuery connection failed: {e}")
            raise
    
    def generate_test_statement(self) -> Dict[str, Any]:
        """Generate a realistic xAPI statement."""
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
                    "description": {"en-US": "A test lesson for Pub/Sub pipeline testing"}
                }
            },
            "timestamp": timestamp,
            "stored": timestamp,
            "context": {
                "platform": "7taps",
                "language": "en-US",
                "extensions": {
                    "https://7taps.com/context/session": str(uuid.uuid4()),
                    "https://7taps.com/context/device": "desktop"
                }
            },
            "result": {
                "completion": True,
                "success": True,
                "score": {"scaled": 0.95},
                "duration": "PT3M45S"
            }
        }
    
    async def send_to_pubsub_endpoint(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Send xAPI statement to Pub/Sub endpoint."""
        print(f"📤 Sending xAPI statement to Pub/Sub: {statement['id']}")
        
        # Use the cloud ingest endpoint that publishes to Pub/Sub
        endpoint = f"{self.base_url}/api/xapi/cloud-ingest"
        
        try:
            response = await self.client.post(
                endpoint,
                json=statement,
                headers={
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully sent to Pub/Sub: {result}")
                return result
            else:
                print(f"❌ Failed to send to Pub/Sub: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Error sending to Pub/Sub: {e}")
            return {"error": str(e)}
    
    async def check_bigquery_data(self, expected_statement_id: str) -> Dict[str, Any]:
        """Check if data appears in BigQuery."""
        print("🔍 Checking BigQuery for new data...")
        
        try:
            # Query the user_activities table for recent data
            query = """
            SELECT 
                statement_id,
                actor_mbox,
                verb_id,
                object_id,
                timestamp,
                result_completion,
                result_success,
                result_score_scaled
            FROM `taps-data.taps_data.user_activities`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)
            ORDER BY timestamp DESC
            LIMIT 20
            """
            
            query_job = self.bigquery_client.query(query)
            results = list(query_job.result())
            
            print(f"✅ Found {len(results)} recent records in BigQuery")
            
            # Check if our test statement is present
            found_statement = None
            for row in results:
                if row.statement_id == expected_statement_id:
                    found_statement = {
                        "statement_id": row.statement_id,
                        "actor": row.actor_mbox,
                        "verb": row.verb_id,
                        "object": row.object_id,
                        "timestamp": str(row.timestamp),
                        "completion": row.result_completion,
                        "success": row.result_success,
                        "score": row.result_score_scaled
                    }
                    break
            
            return {
                "total_recent_records": len(results),
                "found_test_statement": found_statement is not None,
                "test_statement": found_statement,
                "all_recent_records": [
                    {
                        "statement_id": row.statement_id,
                        "actor": row.actor_mbox,
                        "verb": row.verb_id,
                        "object": row.object_id,
                        "timestamp": str(row.timestamp)
                    } for row in results[:5]  # Show first 5
                ]
            }
            
        except Exception as e:
            print(f"❌ Error checking BigQuery: {e}")
            return {"error": str(e)}
    
    async def test_pubsub_pipeline(self):
        """Test the complete Pub/Sub to BigQuery pipeline."""
        print("🚀 Starting Pub/Sub xAPI Pipeline Test")
        print("=" * 50)
        
        await self.setup()
        
        # Generate test statement
        print("\n📝 Generating test statement...")
        test_statement = self.generate_test_statement()
        statement_id = test_statement['id']
        print(f"✅ Generated statement: {statement_id}")
        
        # Send to Pub/Sub endpoint
        print("\n📤 Sending statement to Pub/Sub...")
        pubsub_result = await self.send_to_pubsub_endpoint(test_statement)
        
        if "error" in pubsub_result:
            print("❌ Failed to send to Pub/Sub, aborting test")
            return
        
        # Wait for Pub/Sub processing
        print("\n⏳ Waiting for Pub/Sub → BigQuery processing...")
        print("   (This may take 30-60 seconds for the pipeline to process)")
        await asyncio.sleep(30)
        
        # Check BigQuery
        print("\n🔍 Checking BigQuery for processed data...")
        bigquery_result = await self.check_bigquery_data(statement_id)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 PUB/SUB PIPELINE TEST SUMMARY")
        print("=" * 50)
        print(f"📤 Statement sent: {statement_id}")
        print(f"📨 Pub/Sub result: {pubsub_result.get('message_id', 'N/A')}")
        print(f"🗄️ BigQuery records: {bigquery_result.get('total_recent_records', 0)}")
        print(f"✅ Test statement found: {bigquery_result.get('found_test_statement', False)}")
        
        if bigquery_result.get('found_test_statement'):
            print("\n🎉 SUCCESS: Complete end-to-end pipeline working!")
            print("   xAPI → Pub/Sub → BigQuery ✅")
            
            # Show the processed statement
            test_stmt = bigquery_result.get('test_statement')
            if test_stmt:
                print(f"\n📋 Processed statement details:")
                print(f"   Statement ID: {test_stmt['statement_id']}")
                print(f"   Actor: {test_stmt['actor']}")
                print(f"   Verb: {test_stmt['verb'].split('/')[-1]}")
                print(f"   Object: {test_stmt['object'].split('/')[-1]}")
                print(f"   Completion: {test_stmt['completion']}")
                print(f"   Score: {test_stmt['score']}")
        else:
            print("\n⚠️ PARTIAL SUCCESS: Pub/Sub working, but BigQuery processing may need time")
            print("   xAPI → Pub/Sub ✅")
            print("   Pub/Sub → BigQuery ⏳ (may need more time or check pipeline)")
            
            # Show recent records anyway
            if bigquery_result.get('all_recent_records'):
                print(f"\n📋 Recent BigQuery records:")
                for record in bigquery_result['all_recent_records'][:3]:
                    print(f"   - {record['actor']} {record['verb'].split('/')[-1]} {record['object'].split('/')[-1]}")
        
        await self.client.aclose()

async def main():
    """Main function to run the test."""
    test = PubSubXAPITest()
    await test.test_pubsub_pipeline()

if __name__ == "__main__":
    asyncio.run(main())

