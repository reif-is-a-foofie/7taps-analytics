#!/usr/bin/env python3
"""
Comprehensive xAPI Safety Test Scenarios

Tests real-world learner scenarios to ensure proper flagging
and provides detailed context for incident response.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any

# Test scenarios with realistic learner data
SAFETY_TEST_SCENARIOS = [
    {
        "scenario_name": "Critical Self-Harm - Digital Addiction",
        "learner_context": {
            "name": "Sarah Chen",
            "email": "sarah.chen@student.edu", 
            "user_id": "student_001",
            "course": "Digital Wellness 101",
            "lesson": "Managing Screen Time"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "Sarah Chen",
                "mbox": "mailto:sarah.chen@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/responded",
                "display": {"en-US": "responded"}
            },
            "object": {
                "id": "https://7taps.com/lessons/screen-time",
                "definition": {
                    "name": {"en-US": "Managing Screen Time"},
                    "description": {"en-US": "Learn healthy screen time habits"}
                }
            },
            "result": {
                "response": "I want to kill myself because I can't stop using my phone. I've tried everything but I'm still addicted and it's ruining my life. I don't see any way out of this.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Screen time management",
                    "https://7taps.com/extensions/device-type": "mobile"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Digital Wellness 101",
                "instructor": "Dr. Jane Smith"
            }
        },
        "expected_severity": "critical",
        "expected_flagged": True
    },
    {
        "scenario_name": "High Risk - Depression and Isolation", 
        "learner_context": {
            "name": "Michael Rodriguez",
            "email": "m.rodriguez@student.edu",
            "user_id": "student_002", 
            "course": "Mental Health Awareness",
            "lesson": "Recognizing Depression"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "Michael Rodriguez", 
                "mbox": "mailto:m.rodriguez@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/completed",
                "display": {"en-US": "completed"}
            },
            "object": {
                "id": "https://7taps.com/lessons/depression-signs",
                "definition": {
                    "name": {"en-US": "Recognizing Depression"},
                    "description": {"en-US": "Learn to identify signs of depression"}
                }
            },
            "result": {
                "response": "I feel so depressed and hopeless about everything. I've been isolating myself from friends and family. Nothing seems to matter anymore and I don't know how to get help.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Depression recognition",
                    "https://7taps.com/extensions/previous-responses": "3 previous concerning responses"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Mental Health Awareness",
                "instructor": "Dr. Lisa Johnson"
            }
        },
        "expected_severity": "high",
        "expected_flagged": True
    },
    {
        "scenario_name": "Medium Risk - Academic Stress",
        "learner_context": {
            "name": "Alex Kim",
            "email": "alex.kim@student.edu",
            "user_id": "student_003",
            "course": "Study Skills",
            "lesson": "Managing Academic Pressure"
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
                "id": "https://7taps.com/lessons/academic-stress",
                "definition": {
                    "name": {"en-US": "Managing Academic Pressure"},
                    "description": {"en-US": "Strategies for handling academic stress"}
                }
            },
            "result": {
                "response": "I feel empty inside, like nothing matters anymore. The pressure is too much and I'm struggling to keep up. I don't know if I can handle this semester.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Academic stress management",
                    "https://7taps.com/extensions/gpa": "2.1",
                    "https://7taps.com/extensions/course-load": "18 credits"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Study Skills",
                "instructor": "Prof. David Wilson"
            }
        },
        "expected_severity": "medium", 
        "expected_flagged": True
    },
    {
        "scenario_name": "Normal Learning Response",
        "learner_context": {
            "name": "Emma Thompson",
            "email": "emma.thompson@student.edu",
            "user_id": "student_004",
            "course": "Digital Wellness 101", 
            "lesson": "Healthy Social Media Use"
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
                "id": "https://7taps.com/lessons/social-media-health",
                "definition": {
                    "name": {"en-US": "Healthy Social Media Use"},
                    "description": {"en-US": "Learn to use social media mindfully"}
                }
            },
            "result": {
                "response": "This lesson really helped me understand how social media affects my mood. I'm going to try setting time limits and being more mindful about what I consume.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Social media wellness",
                    "https://7taps.com/extensions/engagement": "high"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Digital Wellness 101",
                "instructor": "Dr. Jane Smith"
            }
        },
        "expected_severity": "low",
        "expected_flagged": False
    },
    {
        "scenario_name": "Metaphorical Expression",
        "learner_context": {
            "name": "James Park",
            "email": "james.park@student.edu",
            "user_id": "student_005", 
            "course": "Study Skills",
            "lesson": "Time Management"
        },
        "xapi_statement": {
            "id": str(uuid.uuid4()),
            "actor": {
                "name": "James Park",
                "mbox": "mailto:james.park@student.edu",
                "objectType": "Agent"
            },
            "verb": {
                "id": "http://adlnet.gov/expapi/verbs/responded", 
                "display": {"en-US": "responded"}
            },
            "object": {
                "id": "https://7taps.com/lessons/time-management",
                "definition": {
                    "name": {"en-US": "Time Management"},
                    "description": {"en-US": "Learn effective time management strategies"}
                }
            },
            "result": {
                "response": "This assignment is killing me with all the work! But I'm learning a lot about how to organize my time better. The techniques are really helpful.",
                "extensions": {
                    "https://7taps.com/extensions/lesson-context": "Time management",
                    "https://7taps.com/extensions/assignment-difficulty": "medium"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "course": "Study Skills", 
                "instructor": "Prof. David Wilson"
            }
        },
        "expected_severity": "low",
        "expected_flagged": False
    }
]

async def test_xapi_safety_scenarios():
    """Test xAPI statements for safety flagging."""
    
    print("🧪 Testing xAPI Safety Scenarios")
    print("=" * 60)
    
    results = []
    
    for i, scenario in enumerate(SAFETY_TEST_SCENARIOS, 1):
        print(f"\n📝 Scenario {i}: {scenario['scenario_name']}")
        print(f"Learner: {scenario['learner_context']['name']} ({scenario['learner_context']['email']})")
        print(f"Course: {scenario['learner_context']['course']}")
        print(f"Expected: {scenario['expected_severity']} severity, flagged: {scenario['expected_flagged']}")
        
        try:
            # Test the xAPI statement analysis
            from app.api.ai_flagged_content import analyze_xapi_statement_content
            
            analysis_result = await analyze_xapi_statement_content(scenario['xapi_statement'])
            
            # Create comprehensive incident report
            incident_report = create_incident_report(scenario, analysis_result)
            
            # Check if results match expectations
            is_flagged = analysis_result.get('is_flagged', False)
            severity = analysis_result.get('severity', 'unknown')
            
            expected_flagged = scenario['expected_flagged']
            expected_severity = scenario['expected_severity']
            
            if is_flagged == expected_flagged and severity == expected_severity:
                print(f"✅ PASS - Correctly flagged as {severity}")
            else:
                print(f"❌ FAIL - Expected {expected_severity}/flagged:{expected_flagged}, got {severity}/flagged:{is_flagged}")
            
            results.append({
                "scenario": scenario['scenario_name'],
                "learner": scenario['learner_context']['name'],
                "expected": {"severity": expected_severity, "flagged": expected_flagged},
                "actual": {"severity": severity, "flagged": is_flagged},
                "analysis": analysis_result,
                "incident_report": incident_report
            })
            
        except Exception as e:
            print(f"❌ ERROR - Test failed: {e}")
            results.append({
                "scenario": scenario['scenario_name'],
                "error": str(e)
            })
    
    # Generate comprehensive report
    print(f"\n📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results if 'error' not in r and 
                r['actual']['severity'] == r['expected']['severity'] and
                r['actual']['flagged'] == r['expected']['flagged'])
    
    total = len(results)
    print(f"Passed: {passed}/{total} scenarios")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"xapi_safety_test_report_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_scenarios": total,
                "passed": passed,
                "failed": total - passed
            },
            "results": results
        }, f, indent=2)
    
    print(f"📄 Detailed report saved to: {report_file}")
    
    return results

def create_incident_report(scenario: Dict[str, Any], analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Create comprehensive incident report for flagged content."""
    
    # Apply privacy masking
    from app.api.privacy_masking import privacy_masker
    
    learner_context = scenario['learner_context']
    masked_data = privacy_masker.mask_pii(
        name=learner_context['name'],
        email=learner_context['email'],
        user_id=learner_context['user_id']
    )
    
    incident_report = {
        "incident_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": analysis_result.get('severity', 'unknown'),
        "confidence_score": analysis_result.get('confidence_score', 0.0),
        
        # Masked learner information
        "learner_info": {
            "masked_name": masked_data['masked_name'],
            "masked_email": masked_data['masked_email'],
            "masked_user_id": masked_data['masked_user_id'],
            "admin_reference": masked_data['admin_reference']
        },
        
        # Educational context
        "educational_context": {
            "course": learner_context['course'],
            "lesson": learner_context['lesson'],
            "instructor": scenario['xapi_statement'].get('context', {}).get('instructor', 'Unknown')
        },
        
        # Flagged content analysis
        "content_analysis": {
            "flagged_reasons": analysis_result.get('flagged_reasons', []),
            "suggested_actions": analysis_result.get('suggested_actions', []),
            "confidence_score": analysis_result.get('confidence_score', 0.0),
            "analysis_notes": analysis_result.get('analysis_metadata', {})
        },
        
        # Original content (for admin review)
        "original_content": {
            "statement_id": scenario['xapi_statement']['id'],
            "response": scenario['xapi_statement']['result']['response'],
            "timestamp": scenario['xapi_statement']['timestamp']
        },
        
        # Response protocol
        "response_protocol": {
            "immediate_actions": [
                "Contact mental health support team",
                "Notify course instructor", 
                "Document incident in student record",
                "Follow up within 24 hours"
            ],
            "escalation_level": get_escalation_level(analysis_result.get('severity', 'unknown')),
            "follow_up_required": analysis_result.get('severity', 'unknown') in ['critical', 'high']
        },
        
        # Privacy compliance
        "privacy_compliance": {
            "data_masked": True,
            "admin_access_required": True,
            "retention_period": "7 years",
            "audit_trail": "maintained"
        }
    }
    
    return incident_report

def get_escalation_level(severity: str) -> str:
    """Determine escalation level based on severity."""
    escalation_map = {
        "critical": "Immediate - Crisis Intervention",
        "high": "Urgent - Within 4 hours", 
        "medium": "Priority - Within 24 hours",
        "low": "Standard - Within 72 hours"
    }
    return escalation_map.get(severity, "Unknown")

if __name__ == "__main__":
    asyncio.run(test_xapi_safety_scenarios())
