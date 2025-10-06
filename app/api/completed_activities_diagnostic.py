"""
Diagnostic tool for tracing completed xAPI activities through the pipeline.
This helps identify where completed activities might be getting lost.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config.gcp_config import get_gcp_config
from app.etl.bigquery_schema_migration import get_migration
from app.api.xapi import recent_statements, ingestion_stats

router = APIRouter()


class CompletedActivityDiagnostic(BaseModel):
    """Diagnostic results for completed activities."""
    total_completed_found: int
    completed_in_recent_memory: int
    completed_in_bigquery: int
    completed_verb_patterns: List[Dict[str, Any]]
    missing_completed_analysis: Dict[str, Any]
    recommendations: List[str]


@router.get("/api/debug/completed-activities", response_model=CompletedActivityDiagnostic)
async def diagnose_completed_activities(
    hours_back: int = Query(24, description="Hours to look back for analysis"),
    verbose: bool = Query(False, description="Include detailed verb analysis")
):
    """
    Comprehensive diagnostic for completed xAPI activities.
    
    This endpoint traces completed activities through:
    1. Recent memory cache
    2. BigQuery storage
    3. Verb pattern analysis
    4. Missing data identification
    """
    try:
        gcp_config = get_gcp_config()
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # 1. Check recent memory cache for completed activities
        completed_in_memory = 0
        completed_verbs_in_memory = {}
        
        for statement_id, statement_data in recent_statements.items():
            if statement_data.get("timestamp"):
                stmt_time = statement_data["timestamp"]
                if isinstance(stmt_time, str):
                    from app.utils.timestamp_utils import parse_timestamp
                    stmt_time = parse_timestamp(stmt_time)
                
                if stmt_time >= cutoff_time:
                    verb_display = statement_data.get("verb", {}).get("display", {})
                    verb_id = statement_data.get("verb", {}).get("id", "")
                    
                    if "completed" in str(verb_display).lower() or "completed" in verb_id.lower():
                        completed_in_memory += 1
                        verb_key = f"{verb_id}|{verb_display}"
                        completed_verbs_in_memory[verb_key] = completed_verbs_in_memory.get(verb_key, 0) + 1
        
        # 2. Check BigQuery for completed activities
        completed_in_bigquery = 0
        completed_verbs_in_bq = {}
        
        try:
            from google.cloud import bigquery
            client = bigquery.Client(credentials=gcp_config.credentials)
            
            # Query for completed activities in the time window
            query = f"""
            SELECT 
                verb_id,
                verb_display,
                COUNT(*) as count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.statements` 
            WHERE timestamp >= '{cutoff_time.isoformat()}'
            AND (LOWER(verb_display) LIKE '%completed%' OR LOWER(verb_id) LIKE '%completed%')
            GROUP BY verb_id, verb_display
            ORDER BY count DESC
            """
            
            for row in client.query(query):
                completed_in_bigquery += row.count
                verb_key = f"{row.verb_id}|{row.verb_display}"
                completed_verbs_in_bq[verb_key] = {
                    "count": row.count,
                    "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                    "last_seen": row.last_seen.isoformat() if row.last_seen else None
                }
                
        except Exception as e:
            completed_verbs_in_bq = {"error": f"BigQuery query failed: {str(e)}"}
        
        # 3. Analyze all verb patterns (not just completed)
        all_verb_patterns = []
        try:
            from google.cloud import bigquery
            client = bigquery.Client(credentials=gcp_config.credentials)
            
            query = f"""
            SELECT 
                verb_id,
                verb_display,
                COUNT(*) as count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen
            FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.statements` 
            WHERE timestamp >= '{cutoff_time.isoformat()}'
            GROUP BY verb_id, verb_display
            ORDER BY count DESC
            LIMIT 20
            """
            
            for row in client.query(query):
                all_verb_patterns.append({
                    "verb_id": row.verb_id,
                    "verb_display": row.verb_display,
                    "count": row.count,
                    "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                    "last_seen": row.last_seen.isoformat() if row.last_seen else None,
                    "is_completed": "completed" in str(row.verb_display).lower() or "completed" in row.verb_id.lower()
                })
                
        except Exception as e:
            all_verb_patterns = [{"error": f"Verb analysis failed: {str(e)}"}]
        
        # 4. Analyze missing completed activities
        total_activities = sum(v.get("count", 0) for v in all_verb_patterns if not v.get("error"))
        completed_activities = sum(v.get("count", 0) for v in all_verb_patterns if v.get("is_completed"))
        completion_rate = (completed_activities / total_activities * 100) if total_activities > 0 else 0
        
        missing_analysis = {
            "total_activities_in_period": total_activities,
            "completed_activities_found": completed_activities,
            "completion_rate_percent": round(completion_rate, 2),
            "expected_completion_rate": "15-25%",  # Based on typical learning analytics
            "gap_analysis": f"{total_activities - completed_activities} activities without completion tracking"
        }
        
        # 5. Generate recommendations
        recommendations = []
        
        if completed_in_memory == 0 and completed_in_bigquery == 0:
            recommendations.append("🚨 CRITICAL: No completed activities found in either memory or BigQuery")
            recommendations.append("Check if your xAPI statements are using the correct 'completed' verb ID")
            recommendations.append("Verify that completed activities are being sent to the ingestion endpoint")
        elif completed_in_memory > 0 and completed_in_bigquery == 0:
            recommendations.append("⚠️ WARNING: Completed activities in memory but not in BigQuery")
            recommendations.append("Check BigQuery ETL pipeline - data may be getting lost during transformation")
            recommendations.append("Verify BigQuery table schema and insertion logic")
        elif completed_in_bigquery > 0 and completed_in_memory == 0:
            recommendations.append("ℹ️ INFO: Completed activities in BigQuery but not in recent memory")
            recommendations.append("This is normal if memory cache has rolled over or app was restarted")
        else:
            recommendations.append("✅ Completed activities found in both memory and BigQuery")
            
        if completion_rate < 10:
            recommendations.append("📊 LOW COMPLETION RATE: Consider checking if completion tracking is properly implemented")
            
        if verbose:
            recommendations.append(f"📈 Total activities processed: {total_activities}")
            recommendations.append(f"🎯 Completed activities found: {completed_activities}")
            recommendations.append(f"📊 Completion rate: {completion_rate:.1f}%")
        
        return CompletedActivityDiagnostic(
            total_completed_found=completed_activities,
            completed_in_recent_memory=completed_in_memory,
            completed_in_bigquery=completed_in_bigquery,
            completed_verb_patterns=all_verb_patterns,
            missing_completed_analysis=missing_analysis,
            recommendations=recommendations
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to diagnose completed activities",
                "error": str(e),
                "recommendations": [
                    "Check GCP credentials and BigQuery access",
                    "Verify the app is running and accessible",
                    "Check logs for ETL processing errors"
                ]
            }
        )


@router.get("/api/debug/completed-activities/sample")
async def get_sample_completed_statement():
    """
    Generate a sample completed xAPI statement for testing.
    Use this to verify your pipeline handles completed activities correctly.
    """
    sample_statement = {
        "id": f"test-completed-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "actor": {
            "objectType": "Agent",
            "id": "https://7taps.com/users/test-user-123",
            "name": "Test User",
            "account": {
                "name": "test-user-123",
                "homePage": "https://7taps.com"
            }
        },
        "verb": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {
                "en-US": "completed"
            }
        },
        "object": {
            "id": "https://7taps.com/lessons/digital-wellness-foundations",
            "objectType": "Activity",
            "definition": {
                "name": {
                    "en-US": "Digital Wellness Foundations"
                },
                "description": {
                    "en-US": "Complete course on digital wellness basics"
                },
                "type": "http://adlnet.gov/expapi/activities/course"
            }
        },
        "result": {
            "success": True,
            "completion": True,
            "score": {
                "scaled": 0.95,
                "raw": 95,
                "min": 0,
                "max": 100
            }
        },
        "context": {
            "platform": "7taps",
            "language": "en-US"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.3"
    }
    
    return {
        "sample_statement": sample_statement,
        "instructions": {
            "test_ingestion": f"POST this to http://localhost:8000/api/xapi/ingest",
            "test_diagnostic": f"Then check http://localhost:8000/api/debug/completed-activities",
            "expected_result": "Should appear in both memory cache and BigQuery within 1-2 minutes"
        }
    }
