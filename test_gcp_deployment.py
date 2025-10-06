#!/usr/bin/env python3
"""
Test script to validate GCP deployment status
"""

import os
import sys
import json
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from google.cloud import pubsub_v1, storage, bigquery
    from google.api_core import exceptions as google_exceptions
    from google.oauth2 import service_account
    from google.auth import default
except ImportError as e:
    print(f"❌ Error importing Google Cloud dependencies: {e}")
    sys.exit(1)

class GCPDeploymentTester:
    """Test GCP deployment status."""
    
    def __init__(self):
        self.project_id = "taps-data"
        self.credentials = self._get_credentials()
        
        # Initialize clients
        try:
            self.pubsub_publisher = pubsub_v1.PublisherClient(credentials=self.credentials)
            self.pubsub_subscriber = pubsub_v1.SubscriberClient(credentials=self.credentials)
            self.storage_client = storage.Client(credentials=self.credentials)
            self.bq_client = bigquery.Client(credentials=self.credentials)
            print("✅ GCP clients initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize GCP clients: {e}")
            sys.exit(1)

    def _get_credentials(self):
        """Get Google Cloud credentials."""
        key_file = os.path.join(os.path.dirname(__file__), 'google-cloud-key.json')

        if os.path.exists(key_file):
            return service_account.Credentials.from_service_account_file(key_file)
        else:
            # Try to use default credentials
            try:
                credentials, _ = default()
                return credentials
            except Exception:
                return None

    def test_pubsub(self):
        """Test Pub/Sub resources."""
        print("\n📡 Testing Pub/Sub resources...")
        
        try:
            # Check topics
            topics = list(self.pubsub_publisher.list_topics(
                request={"project": f"projects/{self.project_id}"}
            ))
            
            topic_names = [t.name.split('/')[-1] for t in topics]
            expected_topics = ["xapi-ingestion-topic"]
            
            print(f"   Found topics: {topic_names}")
            print(f"   Expected topics: {expected_topics}")
            
            # Check subscriptions
            subscriptions = list(self.pubsub_subscriber.list_subscriptions(
                request={"project": f"projects/{self.project_id}"}
            ))
            
            subscription_names = [s.name.split('/')[-1] for s in subscriptions]
            expected_subscriptions = ["xapi-storage-subscriber", "xapi-bigquery-subscriber"]
            
            print(f"   Found subscriptions: {subscription_names}")
            print(f"   Expected subscriptions: {expected_subscriptions}")
            
            return {
                "topics": {"found": topic_names, "expected": expected_topics},
                "subscriptions": {"found": subscription_names, "expected": expected_subscriptions}
            }
        except Exception as e:
            print(f"   ❌ Pub/Sub test failed: {e}")
            return {"error": str(e)}

    def test_storage(self):
        """Test Cloud Storage resources."""
        print("\n🪣 Testing Cloud Storage resources...")
        
        try:
            buckets = list(self.storage_client.list_buckets())
            bucket_names = [b.name for b in buckets]
            expected_buckets = ["taps-data-raw-xapi"]
            
            print(f"   Found buckets: {bucket_names}")
            print(f"   Expected buckets: {expected_buckets}")
            
            return {
                "buckets": {"found": bucket_names, "expected": expected_buckets}
            }
        except Exception as e:
            print(f"   ❌ Storage test failed: {e}")
            return {"error": str(e)}

    def test_bigquery(self):
        """Test BigQuery resources."""
        print("\n📊 Testing BigQuery resources...")
        
        try:
            # Check datasets
            datasets = list(self.bq_client.list_datasets())
            dataset_names = [d.dataset_id for d in datasets]
            expected_datasets = ["taps_data"]
            
            print(f"   Found datasets: {dataset_names}")
            print(f"   Expected datasets: {expected_datasets}")
            
            # Check tables in the main dataset
            tables = []
            if "taps_data" in dataset_names:
                dataset_ref = self.bq_client.dataset("taps_data")
                tables = list(self.bq_client.list_tables(dataset_ref))
            
            table_names = [t.table_id for t in tables]
            expected_tables = ["users", "lessons", "questions", "user_responses", "user_activities", "xapi_events"]
            
            print(f"   Found tables: {table_names}")
            print(f"   Expected tables: {expected_tables}")
            
            return {
                "datasets": {"found": dataset_names, "expected": expected_datasets},
                "tables": {"found": table_names, "expected": expected_tables}
            }
        except Exception as e:
            print(f"   ❌ BigQuery test failed: {e}")
            return {"error": str(e)}

    def run_tests(self):
        """Run all GCP deployment tests."""
        print("🚀 Testing GCP Deployment Status")
        print("=" * 50)
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": self.project_id,
            "tests": {}
        }
        
        # Run tests
        results["tests"]["pubsub"] = self.test_pubsub()
        results["tests"]["storage"] = self.test_storage()
        results["tests"]["bigquery"] = self.test_bigquery()
        
        # Generate summary
        print("\n" + "=" * 50)
        print("📋 DEPLOYMENT SUMMARY")
        print("=" * 50)
        
        for service, test_result in results["tests"].items():
            if "error" in test_result:
                print(f"❌ {service.upper()}: FAILED - {test_result['error']}")
            else:
                print(f"✅ {service.upper()}: Resources accessible")
        
        # Save results
        with open('gcp_deployment_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Test results saved to: gcp_deployment_test_results.json")
        
        return results

if __name__ == '__main__':
    tester = GCPDeploymentTester()
    results = tester.run_tests()
