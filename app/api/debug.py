"""Debug and testing endpoints for the 7taps Analytics API."""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from fastapi import APIRouter

from app.api.bigquery_analytics import (
    get_bigquery_connection_status,
    get_bigquery_integration_status,
)
from app.config import settings


router = APIRouter()
CLOUD_FUNCTION_URL = os.getenv(
    "CLOUD_FUNCTION_URL",
    "https://us-central1-taps-data.cloudfunctions.net/cloud-ingest-xapi",
)


def _utcnow() -> str:
    """Return an ISO formatted UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()

@router.get("/status")
async def debug_status() -> Dict[str, Any]:
    """Get debug status information."""
    return {
        "status": "debug_endpoint_active",
        "timestamp": _utcnow(),
        "environment": settings.ENVIRONMENT,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "version": "1.0.0",
    }

@router.get("/env")
async def debug_environment() -> Dict[str, Any]:
    """Get environment variables (filtered for security)."""
    safe_vars = {}
    for key, value in os.environ.items():
        # Only include non-sensitive variables
        if not any(sensitive in key.lower() for sensitive in ['key', 'secret', 'password', 'token']):
            safe_vars[key] = value
    return safe_vars

@router.get("/health")
async def debug_health() -> Dict[str, Any]:
    """Debug health check."""
    return {
        "status": "healthy",
        "service": "debug",
        "timestamp": _utcnow(),
    }


@router.get("/cloud-run-health")
async def cloud_run_health() -> Dict[str, Any]:
    """Summarize Cloud Run deployment health."""
    bigquery_status = await get_bigquery_connection_status()
    integration_status = await get_bigquery_integration_status()

    healthy_statuses = {"connected", "healthy", "ok", "available"}
    healthy = (
        bigquery_status.get("status") in healthy_statuses
        and integration_status.get("status") in healthy_statuses
    )

    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": _utcnow(),
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "environment": settings.ENVIRONMENT,
        "services": {
            "bigquery_connection": bigquery_status,
            "bigquery_integration": integration_status,
        },
    }


@router.get("/bigquery-integration-health")
async def bigquery_integration_health() -> Dict[str, Any]:
    """Expose BigQuery integration health details."""
    status = await get_bigquery_integration_status()
    return {
        "status": status.get("status", "unknown"),
        "timestamp": _utcnow(),
        "details": status,
    }


@router.get("/cloud-function-health")
async def cloud_function_health() -> Dict[str, Any]:
    """Return cloud function ingestion health."""
    timestamp = _utcnow()
    http_status = 503
    status = "error"
    details: Dict[str, Any] = {"url": CLOUD_FUNCTION_URL}

    # First attempt local health check (useful for local dev environments)
    try:
        from app.api.cloud_function_ingestion import get_cloud_function_status  # local import

        response_json, local_status = get_cloud_function_status()
        details["local_check"] = json.loads(response_json)
        http_status = local_status
        status = "healthy" if local_status == 200 else "error"
    except Exception as exc:  # pragma: no cover - defensive fallback
        details["local_check_error"] = str(exc)

    # When running in Cloud Run, perform an HTTP OPTIONS request to validate ingress
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.options(CLOUD_FUNCTION_URL)
        details["http_check"] = {
            "method": "OPTIONS",
            "status_code": response.status_code,
            "headers": dict(response.headers),
        }
        http_status = response.status_code
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                details["http_response"] = response.json()
            except json.JSONDecodeError:
                details["http_response_text"] = response.text[:256]
        else:
            details["http_response_text"] = response.text[:256]

        if response.status_code < 500:
            status = "healthy"
    except Exception as exc:  # pragma: no cover - network issues
        details["http_check_error"] = str(exc)

    return {
        "status": status,
        "timestamp": timestamp,
        "http_status": http_status,
        "details": details,
    }


@router.get("/production-validation-status")
async def production_validation_status() -> Dict[str, Any]:
    """Aggregate production validation signals for the deployed stack."""
    cloud_run = await cloud_run_health()
    bigquery = await bigquery_integration_health()
    cloud_function = await cloud_function_health()

    signals = {
        "cloud_run": cloud_run,
        "bigquery": bigquery,
        "cloud_function": cloud_function,
    }

    healthy_statuses = {"healthy", "available", "ok", "connected"}
    overall = all(item.get("status") in healthy_statuses for item in signals.values())

    return {
        "status": "operational" if overall else "degraded",
        "timestamp": _utcnow(),
        "environment": settings.ENVIRONMENT,
        "deployment_mode": settings.DEPLOYMENT_MODE,
        "signals": signals,
    }
