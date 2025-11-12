"""
xAPI Ingestion Endpoint for receiving and publishing learning statements.
"""

import asyncio
import uuid
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app.api.cloud_function_ingestion import publish_to_pubsub
from app.api.trigger_word_alerts import trigger_word_alert_manager
from app.api.ai_flagged_content import analyze_xapi_statement_content
from app.config.gcp_config import get_gcp_config
from app.logging_config import get_logger
from app.models import (
    xAPIStatement,
    xAPIIngestionResponse,
    xAPIIngestionStatus,
    xAPIValidationError,
)

logger = get_logger("xapi_ingestion")

# Initialize router
router = APIRouter()

MAX_RECENT_STATEMENTS = 100

ingestion_stats = {
    "total_statements": 0,
    "error_count": 0,
    "last_ingestion_time": None,
    "last_message_id": None,
}
recent_statements: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()


class TriggerWordUpdateRequest(BaseModel):
    words: List[str]
    mode: Optional[str] = "append"


def _serialize_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(alert)
    detected_at = serialized.get("detected_at")
    if isinstance(detected_at, datetime):
        serialized["detected_at"] = detected_at.isoformat()
    return serialized


def _serialize_trigger_word(entry: Dict[str, Any]) -> Dict[str, Any]:
    serialized = dict(entry)
    added_at = serialized.get("added_at")
    if isinstance(added_at, datetime):
        serialized["added_at"] = added_at.isoformat()
    return serialized


def validate_xapi_statement(statement_data: Dict[str, Any]) -> xAPIStatement:
    """Validate xAPI statement data."""
    try:
        return xAPIStatement(**statement_data)
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            errors.append(
                xAPIValidationError(
                    field=error["loc"][0] if error["loc"] else "unknown",
                    message=error["msg"],
                    value=error.get("input"),
                )
            )
        raise HTTPException(
            status_code=422,
            detail={
                "message": "xAPI statement validation failed",
                "errors": [error.model_dump() for error in errors],
            },
        )


async def _prepare_statement_payload(statement: xAPIStatement, *, source: str) -> Dict[str, Any]:
    """Convert statement to a Pub/Sub payload with metadata and AI content analysis."""
    if not statement.id:
        statement.id = str(uuid.uuid4())

    payload = statement.to_dict()
    payload["id"] = statement.id
    payload["ingested_at"] = datetime.now(timezone.utc).isoformat()
    payload["ingestion_source"] = source
    
    # Run AI content analysis for flagged language detection
    try:
        ai_analysis = await analyze_xapi_statement_content(payload)
        payload["ai_content_analysis"] = ai_analysis
        
        # Log flagged content for immediate attention
        if ai_analysis.get("is_flagged", False):
            print(f"🚨 FLAGGED CONTENT DETECTED: {statement.id}")
            print(f"   Severity: {ai_analysis.get('severity', 'unknown')}")
            print(f"   Reasons: {ai_analysis.get('flagged_reasons', [])}")
            print(f"   Confidence: {ai_analysis.get('confidence_score', 0)}")
            
            # Persist flagged content to BigQuery
            try:
                from app.services.flagged_content_persistence import flagged_content_persistence
                
                # Extract content from statement
                content = ""
                result = payload.get("result", {})
                if result.get("response"):
                    content = result["response"]
                
                # Extract actor info
                actor = payload.get("actor", {})
                actor_id = actor.get("mbox", actor.get("mbox_sha1sum", actor.get("openid", "unknown")))
                if actor_id.startswith("mailto:"):
                    actor_id = actor_id[7:]
                actor_name = actor.get("name", None)
                
                # Extract cohort from context extensions
                context = payload.get("context", {})
                extensions = context.get("extensions", {})
                cohort = extensions.get("https://7taps.com/cohort", None)
                
                # Extract timestamp
                timestamp = payload.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now(timezone.utc)
                elif isinstance(timestamp, datetime):
                    pass  # Already a datetime
                elif timestamp is None:
                    timestamp = datetime.now(timezone.utc)
                
                # Persist asynchronously
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        flagged_content_persistence.persist_flagged_content(
                            statement_id=statement.id,
                            timestamp=timestamp,
                            actor_id=actor_id,
                            actor_name=actor_name,
                            content=content,
                            analysis_result=ai_analysis,
                            cohort=cohort
                        )
                    )
                except RuntimeError:
                    # No event loop, skip persistence (shouldn't happen in async context)
                    logger.warning(f"No event loop for persistence, skipping BigQuery write for {statement.id}")
            except Exception as persist_error:
                logger.error(f"Failed to persist flagged content for {statement.id}: {persist_error}")
            
    except Exception as e:
        print(f"⚠️ AI content analysis failed for statement {statement.id}: {e}")
        payload["ai_content_analysis"] = {
            "is_flagged": False,
            "severity": "low",
            "flagged_reasons": ["Analysis failed"],
            "confidence_score": 0.0,
            "error": str(e)
        }
    
    return payload


def _record_ingestion(payload: Dict[str, Any], publish_result: Dict[str, Any]) -> None:
    """Track successful ingestion metrics and recent statements."""
    ingestion_stats["total_statements"] += 1
    ingestion_stats["last_ingestion_time"] = datetime.now(timezone.utc)
    ingestion_stats["last_message_id"] = publish_result.get("message_id")

    recent_statements[payload["id"]] = {
        "payload": payload,
        "message_id": publish_result.get("message_id"),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "statement_id": payload["id"],
    }
    while len(recent_statements) > MAX_RECENT_STATEMENTS:
        recent_statements.popitem(last=False)


def _publish_payload(payload: Dict[str, Any], *, source: str) -> Dict[str, Any]:
    """Publish payload to Pub/Sub and return the publish result."""
    return publish_to_pubsub(payload, source=source)


def publish_statement(statement: xAPIStatement, *, source: str = "api_ingest") -> Dict[str, Any]:
    """Publish a statement to Pub/Sub synchronously."""
    payload = _prepare_statement_payload(statement, source=source)
    try:
        publish_result = _publish_payload(payload, source=source)
    except Exception:
        ingestion_stats["error_count"] += 1
        raise

    _record_ingestion(payload, publish_result)
    return publish_result


async def publish_statement_async(statement: xAPIStatement, *, source: str = "api_ingest") -> Dict[str, Any]:
    """Asynchronously publish a statement to Pub/Sub with AI content analysis."""
    payload = await _prepare_statement_payload(statement, source=source)
    loop = asyncio.get_running_loop()
    try:
        publish_result = await loop.run_in_executor(
            None,
            lambda: _publish_payload(payload, source=source),
        )
    except Exception:
        ingestion_stats["error_count"] += 1
        raise

    _record_ingestion(payload, publish_result)
    return publish_result


@router.post("/api/xapi/ingest", response_model=xAPIIngestionResponse)
async def ingest_xapi_statement(statement_data: Dict[str, Any]):
    """Ingest xAPI statement and publish for downstream ETL processing."""
    try:
        statement = validate_xapi_statement(statement_data)
        publish_result = await publish_statement_async(statement, source="api_ingest_single")

        return xAPIIngestionResponse(
            success=True,
            statement_id=statement.id,
            message=(
                f"xAPI statement published to Pub/Sub topic {publish_result.get('topic')} "
                f"(message {publish_result.get('message_id')})"
            ),
            queue_position=None,
        )

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging path
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to ingest xAPI statement",
                "error": str(exc),
            },
        )


@router.get("/ui/test-xapi-ingestion", response_model=xAPIIngestionStatus)
async def get_xapi_ingestion_status():
    """Get xAPI ingestion endpoint status and statistics."""
    gcp_config = get_gcp_config()

    publisher_ready = False
    try:
        topic_path = gcp_config.get_topic_path()
        publisher = gcp_config.pubsub_publisher
        publisher.get_topic(request={"topic": topic_path})
        publisher_ready = True
    except Exception:
        publisher_ready = False

    status = "operational" if publisher_ready else "error"

    return xAPIIngestionStatus(
        endpoint_status=status,
        publisher_ready=publisher_ready,
        project_id=gcp_config.project_id,
        pubsub_topic=gcp_config.pubsub_topic,
        total_statements_ingested=ingestion_stats["total_statements"],
        last_ingestion_time=ingestion_stats["last_ingestion_time"],
        last_message_id=ingestion_stats.get("last_message_id"),
        error_count=ingestion_stats["error_count"],
    )


@router.post("/api/xapi/ingest/batch")
async def ingest_xapi_batch(statements: List[Dict[str, Any]]):
    """Ingest multiple xAPI statements in batch."""
    results: List[Dict[str, Any]] = []
    success_count = 0
    error_count = 0

    for index, statement_data in enumerate(statements):
        try:
            statement = validate_xapi_statement(statement_data)
            publish_result = await publish_statement_async(statement, source="api_ingest_batch")

            results.append(
                {
                    "index": index,
                    "success": True,
                    "statement_id": statement.id,
                    "message_id": publish_result.get("message_id"),
                }
            )
            success_count += 1
        except Exception as exc:
            results.append(
                {
                    "index": index,
                    "success": False,
                    "error": str(exc),
                }
            )
            error_count += 1

    return {
        "batch_results": results,
        "summary": {
            "total": len(statements),
            "successful": success_count,
            "failed": error_count,
        },
    }


@router.get("/api/xapi/statements/{statement_id}")
async def get_statement_status(statement_id: str):
    """Return the most recent publication metadata for a statement id."""
    record = recent_statements.get(statement_id)
    if record:
        return {
            "found": True,
            "statement_id": statement_id,
            "message_id": record.get("message_id"),
            "published_at": record.get("published_at"),
            "data": record.get("payload"),
        }

    return {
        "found": False,
        "statement_id": statement_id,
        "message": "Statement not found in recent publish history",
    }


def get_ingestion_stats() -> Dict[str, Any]:
    """Get ingestion statistics."""
    return ingestion_stats.copy()


def reset_ingestion_stats() -> None:
    """Reset ingestion statistics and cached statements (for testing)."""
    ingestion_stats.update(
        {
            "total_statements": 0,
            "error_count": 0,
            "last_ingestion_time": None,
            "last_message_id": None,
        }
    )
    recent_statements.clear()


def get_recent_statements(limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent published statements (most recent first)."""
    entries = list(recent_statements.values())
    if limit > 0:
        entries = entries[-limit:]

    ordered = list(reversed(entries))
    return [deepcopy(entry) for entry in ordered]


@router.get("/api/xapi/recent")
async def recent_statements_endpoint(limit: int = 25) -> Dict[str, Any]:
    """Expose recently published xAPI statements."""
    statements = get_recent_statements(limit)
    alerts = [
        _serialize_alert(alert)
        for alert in trigger_word_alert_manager.get_recent_alerts(limit=limit)
    ]
    alert_summary = trigger_word_alert_manager.get_summary()
    latest_alert = alert_summary.get("latest_alert")
    if latest_alert:
        alert_summary["latest_alert"] = _serialize_alert(latest_alert)
    return {
        "statements": statements,
        "limit": limit,
        "available": len(recent_statements),
        "ingestion_stats": get_ingestion_stats(),
        "alerts": alerts,
        "alerts_summary": alert_summary,
    }


@router.get("/api/xapi/alerts/trigger-words")
async def get_trigger_word_alerts(limit: int = 25) -> Dict[str, Any]:
    alerts = [
        _serialize_alert(alert)
        for alert in trigger_word_alert_manager.get_recent_alerts(limit=limit)
    ]
    summary = trigger_word_alert_manager.get_summary()
    latest_alert = summary.get("latest_alert")
    if latest_alert:
        summary["latest_alert"] = _serialize_alert(latest_alert)
    return {
        "trigger_words": [
            _serialize_trigger_word(entry)
            for entry in trigger_word_alert_manager.get_trigger_words()
        ],
        "alerts": alerts,
        "summary": summary,
        "limit": limit,
    }


@router.post("/api/xapi/alerts/trigger-words")
async def update_trigger_words(request: TriggerWordUpdateRequest) -> Dict[str, Any]:
    mode = (request.mode or "append").lower()
    if mode not in {"append", "replace"}:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid mode for trigger word update",
                "allowed_modes": ["append", "replace"],
            },
        )

    result = trigger_word_alert_manager.update_trigger_words(request.words, mode=mode)
    alerts = [
        _serialize_alert(alert)
        for alert in trigger_word_alert_manager.get_recent_alerts()
    ]
    summary = trigger_word_alert_manager.get_summary()
    latest_alert = summary.get("latest_alert")
    if latest_alert:
        summary["latest_alert"] = _serialize_alert(latest_alert)

    return {
        "update_result": result,
        "trigger_words": [
            _serialize_trigger_word(entry)
            for entry in trigger_word_alert_manager.get_trigger_words()
        ],
        "alerts": alerts,
        "summary": summary,
    }
