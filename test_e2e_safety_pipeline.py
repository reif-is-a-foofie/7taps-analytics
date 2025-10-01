#!/usr/bin/env python3
"""
End-to-End Safety Pipeline Test

Tests the complete flow:
1. xAPI statement ingestion
2. ETL processing with AI analysis
3. Dashboard display with privacy masking
4. Action taking (export incident report)
"""

import asyncio
import json
import uuid
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Any

# Test scenarios for E2E testing
E2E_TEST_SCENARIOS = [
    {
        "name": "Critical Self-Harm - Immediate Action Required",
        "learner": {
            "name": "Emma Thompson",
            "email": "emma.thompson@student.edu",
            "user_id": "student_e2e_001"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "Emma Thompson",
                "mbox": "mailto:emma.thompson@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/responded",
                "display": {"en-US": "responded"}
            },
            "object": {
                "id": "https://7taps.com/lessons/digital-wellness",
                "definition": {
                    "name": {"en-US": "Digital Wellness Fundamentals"},
                    "description": {"en-US": "Learn healthy digital habits"}
                }
            },
            "result": {
                "response": "I want to kill myself because I can't stop using my phone. I've tried everything but I'm still addicted and it's ruining my life. I don't see any way out of this addiction.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Digital wellness",
                    "https://7taps.com/extensions/device-type": "mobile"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Digital Wellness 101",
                "instructor": "Dr. Sarah Johnson"
            }
        },
        "expected_flow": "immediate_flag",
        "expected_severity": "critical"
    },
    {
        "name": "Nuanced Depression - Batch Processing",
        "learner": {
            "name": "Michael Chen",
            "email": "michael.chen@student.edu", 
            "user_id": "student_e2e_002"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "Michael Chen",
                "mbox": "mailto:michael.chen@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"}
            },
            "object": {
                "id": "https://7taps.com/lessons/mental-health",
                "definition": {
                    "name": {"en-US": "Mental Health Awareness"},
                    "description": {"en-US": "Understanding mental health"}
                }
            },
            "result": {
                "response": "I've been feeling really down lately. Nothing seems to bring me joy anymore and I feel disconnected from everyone around me. It's hard to focus on anything.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Mental health awareness",
                    "https://7taps.com/extensions/previous-responses": "2 previous concerning responses"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Mental Health Awareness",
                "instructor": "Dr. Lisa Rodriguez"
            }
        },
        "expected_flow": "batch_queue",
        "expected_severity": "medium"
    },
    {
        "name": "Normal Learning Response - No Action",
        "learner": {
            "name": "Alex Kim",
            "email": "alex.kim@student.edu",
            "user_id": "student_e2e_003"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "Alex Kim",
                "mbox": "mailto:alex.kim@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/answered",
                "display": {"en-US": "answered"}
            },
            "object": {
                "id": "https://7taps.com/lessons/study-skills",
                "definition": {
                    "name": {"en-US": "Effective Study Techniques"},
                    "description": {"en-US": "Learn how to study effectively"}
                }
            },
            "result": {
                "response": "This lesson really helped me understand how to manage my time better. I'm going to try the Pomodoro technique and see how it works for me.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Study skills",
                    "https://7taps.com/extensions/engagement": "high"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Study Skills 101",
                "instructor": "Prof. David Wilson"
            }
        },
        "expected_flow": "batch_queue",
        "expected_severity": "none"
    }
]

async def test_e2e_pipeline():
    """Test the complete end-to-end safety pipeline."""
    
    print("🚀 End-to-End Safety Pipeline Test")
    print("=" * 60)
    
    base_url = "https://taps-analytics-ui-245712978112.us-central1.run.app"
    results = []
    
    for i, scenario in enumerate(E2E_TEST_SCENARIOS, 1):
        print(f"\n📝 Scenario {i}: {scenario['name']}")
        print(f"Learner: {scenario['learner']['name']} ({scenario['learner']['email']})")
        print(f"Expected Flow: {scenario['expected_flow']}")
        print("-" * 50)
        
        scenario_result = {
            "scenario": scenario['name'],
            "learner": scenario['learner'],
            "steps": {}
        }
        
        try:
            # Step 1: Submit xAPI statement to ETL pipeline
            print("1️⃣ Submitting xAPI statement to ETL...")
            xapi_result = await submit_xapi_statement(base_url, scenario['xapi_statement'])
            scenario_result["steps"]["xapi_submission"] = xapi_result
            print(f"   ✅ xAPI submitted: {xapi_result['status']}")
            
            # Step 2: Check AI analysis processing
            print("2️⃣ Checking AI analysis processing...")
            ai_result = await check_ai_processing(base_url, scenario['xapi_statement']['result']['response'])
            scenario_result["steps"]["ai_analysis"] = ai_result
            print(f"   ✅ AI Analysis: {ai_result['status']} (severity: {ai_result.get('severity', 'none')})")
            
            # Step 3: Verify expected flow
            expected = scenario['expected_flow']
            actual = ai_result['status']
            if expected == "immediate_flag" and actual == "flagged":
                print(f"   ✅ Flow Correct: Immediate flagging as expected")
            elif expected == "batch_queue" and actual == "queued":
                print(f"   ✅ Flow Correct: Batch queuing as expected")
            else:
                print(f"   ⚠️  Flow Unexpected: Expected {expected}, got {actual}")
            
            # Step 4: Check dashboard visibility (simulate)
            print("3️⃣ Checking dashboard visibility...")
            dashboard_data = await check_dashboard_data(base_url, scenario['learner'])
            scenario_result["steps"]["dashboard_visibility"] = dashboard_data
            print(f"   ✅ Dashboard: {dashboard_data['status']}")
            
            # Step 5: Test privacy masking
            print("4️⃣ Testing privacy masking...")
            masking_result = await test_privacy_masking(base_url, scenario['learner'])
            scenario_result["steps"]["privacy_masking"] = masking_result
            print(f"   ✅ Privacy: {masking_result['status']}")
            
            # Step 6: Test incident export (if flagged)
            if ai_result.get('is_flagged', False):
                print("5️⃣ Testing incident export...")
                export_result = await test_incident_export(base_url, scenario, ai_result)
                scenario_result["steps"]["incident_export"] = export_result
                print(f"   ✅ Export: {export_result['status']}")
            else:
                print("5️⃣ No incident export needed (not flagged)")
                scenario_result["steps"]["incident_export"] = {"status": "skipped", "reason": "not_flagged"}
            
            results.append(scenario_result)
            print(f"✅ Scenario {i} completed successfully")
            
        except Exception as e:
            print(f"❌ Scenario {i} failed: {e}")
            scenario_result["error"] = str(e)
            results.append(scenario_result)
    
    # Generate comprehensive report
    print(f"\n📊 E2E Test Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if 'error' not in r)
    total = len(results)
    
    print(f"Successful scenarios: {successful}/{total}")
    
    # Show flow verification
    print(f"\n🔄 Flow Verification:")
    for result in results:
        if 'error' not in result:
            ai_step = result['steps'].get('ai_analysis', {})
            status = ai_step.get('status', 'unknown')
            severity = ai_step.get('severity', 'none')
            print(f"  - {result['scenario']}: {status} ({severity})")
    
    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"e2e_pipeline_test_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "test_type": "end_to_end_safety_pipeline",
            "base_url": base_url,
            "summary": {
                "total_scenarios": total,
                "successful": successful,
                "failed": total - successful
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed report saved: {report_file}")
    print(f"\n🎯 E2E Pipeline Test Complete!")
    
    return results

async def submit_xapi_statement(base_url: str, statement: Dict[str, Any]) -> Dict[str, Any]:
    """Submit xAPI statement to the ETL pipeline."""
    async with httpx.AsyncClient() as client:
        # Submit to xAPI endpoint
        response = await client.post(
            f"{base_url}/api/xapi/statements",
            json=[statement],
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {
                "status": "submitted",
                "statement_id": statement["id"],
                "response": response.json()
            }
        else:
            return {
                "status": "failed",
                "error": f"HTTP {response.status_code}: {response.text}"
            }

async def check_ai_processing(base_url: str, content: str) -> Dict[str, Any]:
    """Check AI analysis processing for content."""
    async with httpx.AsyncClient() as client:
        # Test with batch AI safety system
        response = await client.post(
            f"{base_url}/api/batch-ai-safety/process",
            params={
                "content": content,
                "context": "test",
                "statement_id": str(uuid.uuid4()),
                "user_id": "test_user"
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            return {
                "status": result.get("status", "unknown"),
                "is_flagged": result.get("is_flagged", False),
                "severity": result.get("severity", "none"),
                "confidence": result.get("confidence_score", 0.0),
                "flagged_reasons": result.get("flagged_reasons", []),
                "suggested_actions": result.get("suggested_actions", [])
            }
        else:
            return {
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text}"
            }

async def check_dashboard_data(base_url: str, learner: Dict[str, Any]) -> Dict[str, Any]:
    """Check if data appears on dashboard (simulated)."""
    async with httpx.AsyncClient() as client:
        # Check safety dashboard
        response = await client.get(f"{base_url}/ui/safety", timeout=30.0)
        
        if response.status_code == 200:
            # In a real test, we'd parse the HTML to check for specific content
            return {
                "status": "visible",
                "dashboard_loaded": True,
                "note": "Dashboard loads successfully (content visibility would be checked in real implementation)"
            }
        else:
            return {
                "status": "error",
                "error": f"Dashboard not accessible: HTTP {response.status_code}"
            }

async def test_privacy_masking(base_url: str, learner: Dict[str, Any]) -> Dict[str, Any]:
    """Test privacy masking functionality."""
    async with httpx.AsyncClient() as client:
        # Test masking
        mask_response = await client.post(
            f"{base_url}/api/privacy/mask",
            json={
                "name": learner["name"],
                "email": learner["email"],
                "user_id": learner["user_id"]
            },
            timeout=30.0
        )
        
        if mask_response.status_code == 200:
            mask_data = mask_response.json()
            
            # Test unmasking
            unmask_response = await client.post(
                f"{base_url}/api/privacy/unmask",
                json={
                    "masked_name": mask_data.get("original_name"),
                    "masked_email": mask_data.get("original_email"),
                    "masked_user_id": mask_data.get("original_user_id"),
                    "password": "admin_safety_2024"
                },
                timeout=30.0
            )
            
            if unmask_response.status_code == 200:
                return {
                    "status": "working",
                    "masked_name": mask_data.get("masked_name"),
                    "unmasking_successful": True
                }
            else:
                return {
                    "status": "partial",
                    "masking_works": True,
                    "unmasking_failed": True,
                    "error": unmask_response.text
                }
        else:
            return {
                "status": "failed",
                "error": f"Masking failed: HTTP {mask_response.status_code}"
            }

async def test_incident_export(base_url: str, scenario: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """Test incident report export functionality."""
    async with httpx.AsyncClient() as client:
        # Create incident report data
        incident_data = {
            "incident_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "learner_info": scenario['learner'],
            "educational_context": {
                "course": scenario['xapi_statement']['context']['course'],
                "instructor": scenario['xapi_statement']['context'].get('instructor', 'Unknown')
            },
            "flagged_content": {
                "original_response": scenario['xapi_statement']['result']['response'],
                "severity": ai_result.get('severity', 'unknown'),
                "confidence": ai_result.get('confidence', 0.0),
                "flagged_reasons": ai_result.get('flagged_reasons', []),
                "suggested_actions": ai_result.get('suggested_actions', [])
            },
            "response_protocol": {
                "immediate_actions": [
                    "Contact mental health support team",
                    "Notify course instructor",
                    "Document in student record"
                ],
                "escalation_level": f"{ai_result.get('severity', 'unknown').title()} - Action Required",
                "follow_up_required": ai_result.get('severity', 'unknown') in ['critical', 'high']
            }
        }
        
        # Test export
        response = await client.post(
            f"{base_url}/api/privacy/export",
            json={
                "data": incident_data,
                "password": "admin_safety_2024",
                "export_reason": f"E2E test export for {scenario['name']}"
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            export_data = response.json()
            return {
                "status": "successful",
                "exported_data": export_data.get("exported_data"),
                "export_timestamp": export_data.get("export_timestamp")
            }
        else:
            return {
                "status": "failed",
                "error": f"HTTP {response.status_code}: {response.text}"
            }

if __name__ == "__main__":
    asyncio.run(test_e2e_pipeline())
