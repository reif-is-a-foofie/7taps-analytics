#!/usr/bin/env python3
"""
Standalone test script for GCP monitoring endpoints
This tests the monitoring functionality without requiring the full FastAPI server
"""

import os
import sys
import json
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the monitoring module directly
from app.api.gcp_monitoring import GCPHealthChecker

def test_monitoring_endpoints():
    """Test all monitoring endpoint functionality."""
    print("🔍 Testing GCP Monitoring Endpoints")
    print("=" * 50)
    
    # Initialize health checker
    health_checker = GCPHealthChecker()
    
    # Test 1: Infrastructure Status
    print("\n1️⃣ Testing Infrastructure Status...")
    try:
        status = health_checker.get_overall_health()
        print(f"   ✅ Overall Status: {status['overall_status']}")
        print(f"   📊 Project ID: {status['project_id']}")
        print(f"   🕐 Timestamp: {status['timestamp']}")
        
        # Save result
        with open('infrastructure_status_test.json', 'w') as f:
            json.dump(status, f, indent=2, default=str)
        print("   📄 Result saved to: infrastructure_status_test.json")
        
    except Exception as e:
        print(f"   ❌ Infrastructure status test failed: {e}")
    
    # Test 2: Resource Health
    print("\n2️⃣ Testing Resource Health...")
    try:
        pubsub_health = health_checker.check_pubsub_health()
        storage_health = health_checker.check_storage_health()
        bigquery_health = health_checker.check_bigquery_health()
        
        health_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pubsub": pubsub_health,
            "storage": storage_health,
            "bigquery": bigquery_health
        }
        
        print(f"   ✅ Pub/Sub Status: {pubsub_health.get('status', 'unknown')}")
        print(f"   ✅ Storage Status: {storage_health.get('status', 'unknown')}")
        print(f"   ✅ BigQuery Status: {bigquery_health.get('status', 'unknown')}")
        
        # Save result
        with open('resource_health_test.json', 'w') as f:
            json.dump(health_info, f, indent=2, default=str)
        print("   📄 Result saved to: resource_health_test.json")
        
    except Exception as e:
        print(f"   ❌ Resource health test failed: {e}")
    
    # Test 3: Deployment Validation
    print("\n3️⃣ Testing Deployment Validation...")
    try:
        validation_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validation_passed": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check each component
        pubsub_health = health_checker.check_pubsub_health()
        storage_health = health_checker.check_storage_health()
        bigquery_health = health_checker.check_bigquery_health()
        
        # Collect issues
        if pubsub_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("Pub/Sub service is not accessible")
        
        if storage_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("Cloud Storage service is not accessible")
        elif storage_health.get("status") == "partial":
            validation_results["recommendations"].append("Some Cloud Storage buckets are missing - check billing account")
        
        if bigquery_health.get("status") == "error":
            validation_results["validation_passed"] = False
            validation_results["issues"].append("BigQuery service is not accessible")
        elif bigquery_health.get("status") == "partial":
            validation_results["recommendations"].append("Some BigQuery tables are missing")
        
        # Add component details
        validation_results["components"] = {
            "pubsub": pubsub_health,
            "storage": storage_health,
            "bigquery": bigquery_health
        }
        
        print(f"   ✅ Validation Passed: {validation_results['validation_passed']}")
        print(f"   📋 Issues: {len(validation_results['issues'])}")
        print(f"   💡 Recommendations: {len(validation_results['recommendations'])}")
        
        # Save result
        with open('deployment_validation_test.json', 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        print("   📄 Result saved to: deployment_validation_test.json")
        
    except Exception as e:
        print(f"   ❌ Deployment validation test failed: {e}")
    
    # Test 4: Deployment Summary
    print("\n4️⃣ Testing Deployment Summary...")
    try:
        health = health_checker.get_overall_health()
        
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": health["project_id"],
            "overall_status": health["overall_status"],
            "deployment_complete": health["overall_status"] in ["healthy", "partial"],
            "components_status": {
                "pubsub": health["components"]["pubsub"]["status"],
                "storage": health["components"]["storage"]["status"],
                "bigquery": health["components"]["bigquery"]["status"]
            },
            "next_steps": []
        }
        
        # Add next steps based on status
        if health["overall_status"] == "error":
            summary["next_steps"].append("Check GCP credentials and project permissions")
        elif health["overall_status"] == "partial":
            summary["next_steps"].append("Complete missing resource creation")
            if health["components"]["storage"]["status"] != "healthy":
                summary["next_steps"].append("Enable billing account for Cloud Storage")
        else:
            summary["next_steps"].append("Deploy Cloud Function for xAPI ingestion")
            summary["next_steps"].append("Test end-to-end data flow")
        
        print(f"   ✅ Overall Status: {summary['overall_status']}")
        print(f"   ✅ Deployment Complete: {summary['deployment_complete']}")
        print(f"   📋 Next Steps: {len(summary['next_steps'])}")
        
        # Save result
        with open('deployment_summary_test.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print("   📄 Result saved to: deployment_summary_test.json")
        
    except Exception as e:
        print(f"   ❌ Deployment summary test failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 MONITORING ENDPOINTS TEST COMPLETE!")
    print("=" * 50)
    print("All monitoring endpoint functionality has been tested.")
    print("Check the generated JSON files for detailed results.")

if __name__ == '__main__':
    test_monitoring_endpoints()
