#!/usr/bin/env python3
"""
Simple xAPI Safety Test

Tests xAPI flagging without privacy masking for now.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

async def test_xapi_flagging():
    """Test xAPI flagging with real scenarios."""
    
    print("🧪 Testing xAPI Safety Flagging")
    print("=" * 50)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Critical Self-Harm",
            "content": "I want to kill myself because I can't stop using my phone",
            "expected": "critical"
        },
        {
            "name": "Depression Expression", 
            "content": "I feel so depressed and hopeless about everything",
            "expected": "critical"
        },
        {
            "name": "Normal Learning",
            "content": "This lesson is challenging but I'm learning a lot",
            "expected": "queued"
        },
        {
            "name": "Metaphorical",
            "content": "This assignment is killing me with all the work",
            "expected": "queued"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['name']}")
        print(f"Content: \"{scenario['content']}\"")
        
        try:
            # Create xAPI statement
            xapi_statement = {
                "id": str(uuid.uuid4()),
                "actor": {
                    "name": f"Test User {i}",
                    "mbox": f"mailto:test{i}@student.edu",
                    "objectType": "Agent"
                },
                "verb": {
                    "id": "http://adlnet.gov/expapi/verbs/responded",
                    "display": {"en-US": "responded"}
                },
                "object": {
                    "id": "https://7taps.com/lessons/test",
                    "definition": {
                        "name": {"en-US": "Test Lesson"},
                        "description": {"en-US": "Test lesson for safety analysis"}
                    }
                },
                "result": {
                    "response": scenario['content']
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Analyze with batch system
            from app.api.ai_flagged_content import analyze_xapi_statement_content
            
            analysis = await analyze_xapi_statement_content(xapi_statement)
            
            status = analysis.get('status', 'unknown')
            severity = analysis.get('severity', 'unknown')
            
            print(f"Result: {status} (severity: {severity})")
            
            # Create incident context for flagged content
            if analysis.get('is_flagged', False):
                incident_context = {
                    "incident_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "learner_info": {
                        "name": f"Test User {i}",
                        "email": f"test{i}@student.edu",
                        "user_id": f"student_{i:03d}"
                    },
                    "educational_context": {
                        "course": "Digital Wellness 101",
                        "lesson": "Test Lesson",
                        "instructor": "Dr. Test Instructor"
                    },
                    "flagged_content": {
                        "original_response": scenario['content'],
                        "severity": severity,
                        "confidence": analysis.get('confidence_score', 0.0),
                        "flagged_reasons": analysis.get('flagged_reasons', []),
                        "suggested_actions": analysis.get('suggested_actions', [])
                    },
                    "response_protocol": {
                        "immediate_actions": [
                            "Contact mental health support team",
                            "Notify course instructor",
                            "Document in student record"
                        ],
                        "escalation_level": get_escalation_level(severity),
                        "follow_up_required": severity in ['critical', 'high']
                    }
                }
                
                print(f"🚨 INCIDENT REPORT CREATED:")
                print(f"   - Severity: {severity}")
                print(f"   - Confidence: {analysis.get('confidence_score', 0.0):.1%}")
                print(f"   - Actions: {len(analysis.get('suggested_actions', []))} recommended")
                print(f"   - Escalation: {get_escalation_level(severity)}")
                
                results.append({
                    "scenario": scenario['name'],
                    "flagged": True,
                    "severity": severity,
                    "incident_context": incident_context
                })
            else:
                print(f"✅ Content cleared - no action needed")
                results.append({
                    "scenario": scenario['name'],
                    "flagged": False,
                    "status": status
                })
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "scenario": scenario['name'],
                "error": str(e)
            })
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    
    flagged_count = sum(1 for r in results if r.get('flagged', False))
    total_count = len(results)
    
    print(f"Total scenarios: {total_count}")
    print(f"Flagged content: {flagged_count}")
    print(f"Cleared content: {total_count - flagged_count}")
    
    if flagged_count > 0:
        print(f"\n🚨 Incident Response Summary:")
        for result in results:
            if result.get('flagged'):
                context = result['incident_context']
                print(f"  - {result['scenario']}: {context['flagged_content']['severity']} severity")
                print(f"    Actions: {', '.join(context['response_protocol']['immediate_actions'][:2])}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"xapi_simple_test_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_scenarios": total_count,
                "flagged_count": flagged_count,
                "cleared_count": total_count - flagged_count
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n📄 Report saved: {report_file}")

def get_escalation_level(severity: str) -> str:
    """Get escalation level based on severity."""
    levels = {
        "critical": "Immediate - Crisis Intervention",
        "high": "Urgent - Within 4 hours",
        "medium": "Priority - Within 24 hours", 
        "low": "Standard - Within 72 hours"
    }
    return levels.get(severity, "Unknown")

if __name__ == "__main__":
    asyncio.run(test_xapi_flagging())
