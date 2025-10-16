"""
Cohort-based safety and trigger word management.
Each cohort can have its own set of trigger words and safety rules.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

from app.logging_config import get_logger

logger = get_logger("cohort_safety")
router = APIRouter()

COHORT_TRIGGER_WORDS_FILE = Path("app/data/cohort_trigger_words.json")


class CohortTriggerWord(BaseModel):
    word: str
    severity: str = "medium"
    description: Optional[str] = None


class CohortSafetyConfig(BaseModel):
    cohort_id: str
    name: str
    description: Optional[str] = None
    words: List[CohortTriggerWord] = []


def load_cohort_trigger_words() -> Dict[str, Any]:
    """Load cohort trigger words from file."""
    try:
        if COHORT_TRIGGER_WORDS_FILE.exists():
            with open(COHORT_TRIGGER_WORDS_FILE, 'r') as f:
                return json.load(f)
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "cohorts": {}}
    except Exception as e:
        logger.error(f"Error loading cohort trigger words: {e}")
        return {"timestamp": datetime.now(timezone.utc).isoformat(), "cohorts": {}}


def save_cohort_trigger_words(data: Dict[str, Any]) -> None:
    """Save cohort trigger words to file."""
    try:
        COHORT_TRIGGER_WORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(COHORT_TRIGGER_WORDS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cohort trigger words: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save: {str(e)}")


@router.get("/api/cohorts/safety")
async def get_all_cohort_safety_configs() -> Dict[str, Any]:
    """Get safety configurations for all cohorts."""
    try:
        data = load_cohort_trigger_words()
        cohorts = data.get("cohorts", {})
        
        return {
            "success": True,
            "cohorts": cohorts,
            "total_cohorts": len(cohorts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cohort safety configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/cohorts/{cohort_id}/safety")
async def get_cohort_safety_config(cohort_id: str) -> Dict[str, Any]:
    """Get safety configuration for a specific cohort."""
    try:
        data = load_cohort_trigger_words()
        cohorts = data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            # Return default empty config
            return {
                "success": True,
                "cohort_id": cohort_id,
                "name": cohort_id,
                "description": f"Safety config for {cohort_id}",
                "words": [],
                "inherited_from_default": True
            }
        
        config = cohorts[cohort_id]
        return {
            "success": True,
            "cohort_id": cohort_id,
            **config,
            "total_words": len(config.get("words", []))
        }
    except Exception as e:
        logger.error(f"Error getting cohort safety config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/cohorts/{cohort_id}/safety/words")
async def add_cohort_trigger_word(
    cohort_id: str,
    word: str = Query(..., description="Trigger word to add"),
    severity: str = Query("medium", description="Severity: low, medium, high"),
    description: Optional[str] = Query(None, description="Description")
) -> Dict[str, Any]:
    """Add a trigger word to a specific cohort."""
    try:
        data = load_cohort_trigger_words()
        cohorts = data.get("cohorts", {})
        
        # Create cohort if it doesn't exist
        if cohort_id not in cohorts:
            cohorts[cohort_id] = {
                "name": cohort_id,
                "description": f"Safety config for {cohort_id}",
                "words": []
            }
        
        cohort_config = cohorts[cohort_id]
        words = cohort_config.get("words", [])
        
        # Check if word already exists
        for existing_word in words:
            if existing_word["word"].lower() == word.lower():
                raise HTTPException(
                    status_code=400, 
                    detail=f"Word '{word}' already exists for cohort '{cohort_id}'"
                )
        
        # Add new word
        new_word = {
            "word": word,
            "severity": severity,
            "description": description or "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "active": True
        }
        
        words.append(new_word)
        cohort_config["words"] = words
        cohorts[cohort_id] = cohort_config
        data["cohorts"] = cohorts
        
        save_cohort_trigger_words(data)
        
        logger.info(f"Added trigger word '{word}' to cohort '{cohort_id}'")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' added to cohort '{cohort_id}'",
            "cohort_id": cohort_id,
            "word": new_word,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding cohort trigger word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/cohorts/{cohort_id}/safety/words/{word}")
async def remove_cohort_trigger_word(cohort_id: str, word: str) -> Dict[str, Any]:
    """Remove a trigger word from a specific cohort."""
    try:
        data = load_cohort_trigger_words()
        cohorts = data.get("cohorts", {})
        
        if cohort_id not in cohorts:
            raise HTTPException(status_code=404, detail=f"Cohort '{cohort_id}' not found")
        
        cohort_config = cohorts[cohort_id]
        words = cohort_config.get("words", [])
        
        # Remove word
        updated_words = [w for w in words if w["word"].lower() != word.lower()]
        
        if len(updated_words) == len(words):
            raise HTTPException(
                status_code=404,
                detail=f"Word '{word}' not found in cohort '{cohort_id}'"
            )
        
        cohort_config["words"] = updated_words
        cohorts[cohort_id] = cohort_config
        data["cohorts"] = cohorts
        
        save_cohort_trigger_words(data)
        
        logger.info(f"Removed trigger word '{word}' from cohort '{cohort_id}'")
        
        return {
            "success": True,
            "message": f"Trigger word '{word}' removed from cohort '{cohort_id}'",
            "cohort_id": cohort_id,
            "word": word,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing cohort trigger word: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/cohorts/{cohort_id}/flagged-content")
async def get_cohort_flagged_content(
    cohort_id: str,
    limit: int = Query(50, ge=1, le=500),
    severity: Optional[str] = Query(None, description="Filter by severity")
) -> Dict[str, Any]:
    """Get flagged content for a specific cohort."""
    try:
        from app.config.gcp_config import gcp_config
        from google.cloud import bigquery
        
        client = bigquery.Client(project=gcp_config.project_id)
        
        # Build query to get flagged statements for cohort
        severity_filter = ""
        if severity:
            severity_filter = f"AND JSON_EXTRACT_SCALAR(ai_content_analysis, '$.severity') = '{severity}'"
        
        query = f"""
        SELECT 
            statement_id,
            actor_name,
            timestamp,
            JSON_EXTRACT_SCALAR(result, '$.response') as content,
            JSON_EXTRACT_SCALAR(ai_content_analysis, '$.severity') as severity,
            JSON_EXTRACT(ai_content_analysis, '$.flagged_reasons') as flagged_reasons,
            JSON_EXTRACT_SCALAR(ai_content_analysis, '$.confidence_score') as confidence_score,
            JSON_EXTRACT(context_extensions, '$."https://7taps.com/cohort"') as cohort
        FROM `{gcp_config.project_id}.{gcp_config.bigquery_dataset}.xapi_statements`
        WHERE JSON_EXTRACT_SCALAR(ai_content_analysis, '$.is_flagged') = 'true'
            AND JSON_EXTRACT(context_extensions, '$."https://7taps.com/cohort"') = '"{cohort_id}"'
            {severity_filter}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """
        
        query_job = client.query(query)
        results = list(query_job.result())
        
        flagged_content = []
        for row in results:
            flagged_content.append({
                "statement_id": row["statement_id"],
                "actor_name": row["actor_name"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "content": row["content"],
                "severity": row["severity"],
                "flagged_reasons": json.loads(row["flagged_reasons"]) if row["flagged_reasons"] else [],
                "confidence_score": float(row["confidence_score"]) if row["confidence_score"] else 0.0,
                "cohort": cohort_id
            })
        
        return {
            "success": True,
            "cohort_id": cohort_id,
            "flagged_content": flagged_content,
            "total_count": len(flagged_content),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting cohort flagged content: {e}")
        return {
            "success": False,
            "error": str(e),
            "cohort_id": cohort_id,
            "flagged_content": [],
            "total_count": 0
        }


@router.get("/api/cohorts/{cohort_id}/flagged-content/export")
async def export_cohort_flagged_content(
    cohort_id: str,
    format: str = Query("csv", description="Export format: csv or json")
) -> Any:
    """Export flagged content for a cohort."""
    try:
        from fastapi.responses import Response
        import csv
        import io
        
        # Get flagged content
        result = await get_cohort_flagged_content(cohort_id, limit=500)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to fetch flagged content")
        
        flagged_content = result.get("flagged_content", [])
        
        if format == "csv":
            # Generate CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=["statement_id", "actor_name", "timestamp", "content", 
                           "severity", "flagged_reasons", "confidence_score", "cohort"]
            )
            writer.writeheader()
            
            for item in flagged_content:
                item_copy = item.copy()
                item_copy["flagged_reasons"] = "; ".join(item_copy.get("flagged_reasons", []))
                writer.writerow(item_copy)
            
            csv_content = output.getvalue()
            
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=flagged_content_{cohort_id}_{datetime.now().strftime('%Y%m%d')}.csv"
                }
            )
        
        else:  # JSON
            return Response(
                content=json.dumps({
                    "cohort_id": cohort_id,
                    "export_date": datetime.now(timezone.utc).isoformat(),
                    "flagged_content": flagged_content
                }, indent=2),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=flagged_content_{cohort_id}_{datetime.now().strftime('%Y%m%d')}.json"
                }
            )
        
    except Exception as e:
        logger.error(f"Error exporting cohort flagged content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


