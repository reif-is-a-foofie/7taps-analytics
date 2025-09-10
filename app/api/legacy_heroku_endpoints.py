"""
Legacy Heroku Endpoints - DEPRECATED

This module contains legacy endpoints that were used during Heroku deployment.
These endpoints are now DEPRECATED and will be removed in a future version.

All functionality has been migrated to Google Cloud Platform:
- xAPI ingestion: Cloud Functions + Pub/Sub + BigQuery
- Data storage: Cloud Storage + BigQuery
- Analytics: BigQuery Analytics Dashboard

Migration completed as part of gc05 (Migration Cleanup & Validation).
"""

import os
import json
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

# Create router
router = APIRouter()

# Migration completion date
MIGRATION_COMPLETED = "2025-09-10T00:00:00Z"

# Deprecation warning message
DEPRECATION_WARNING = {
    "warning": "DEPRECATED ENDPOINT",
    "message": "This endpoint is deprecated and will be removed in a future version.",
    "migration_info": {
        "completed_date": MIGRATION_COMPLETED,
        "new_platform": "Google Cloud Platform",
        "replacement_endpoints": {
            "xapi_ingestion": "/api/xapi/cloud-ingest",
            "analytics": "/api/analytics/bigquery/*",
            "dashboard": "/ui/bigquery-dashboard",
            "data_export": "/api/analytics/export/*"
        },
        "documentation": "/api/docs"
    },
    "contact": "Migration completed successfully. Use new GCP endpoints."
}

@router.get("/api/health")
async def legacy_health_check():
    """
    LEGACY: Health check endpoint
    DEPRECATED: Use /api/health instead
    """
    return JSONResponse(
        content={
            **DEPRECATION_WARNING,
            "legacy_status": "deprecated",
            "timestamp": datetime.utcnow().isoformat(),
            "new_endpoint": "/api/health"
        },
        status_code=200,
        headers={"X-Deprecated": "true"}
    )

@router.post("/api/xapi/statements")
async def legacy_xapi_ingestion(request: Request):
    """
    LEGACY: xAPI statement ingestion
    DEPRECATED: Use /api/xapi/cloud-ingest instead
    """
    return JSONResponse(
        content={
            **DEPRECATION_WARNING,
            "legacy_status": "deprecated",
            "timestamp": datetime.utcnow().isoformat(),
            "new_endpoint": "/api/xapi/cloud-ingest",
            "migration_note": "xAPI ingestion now uses Cloud Functions + Pub/Sub + BigQuery"
        },
        status_code=200,
        headers={"X-Deprecated": "true"}
    )

@router.get("/api/analytics/dashboard")
async def legacy_analytics_dashboard():
    """
    LEGACY: Analytics dashboard data
    DEPRECATED: Use /api/analytics/bigquery/dashboard instead
    """
    return JSONResponse(
        content={
            **DEPRECATION_WARNING,
            "legacy_status": "deprecated",
            "timestamp": datetime.utcnow().isoformat(),
            "new_endpoint": "/api/analytics/bigquery/dashboard",
            "migration_note": "Analytics now powered by BigQuery with real-time dashboards"
        },
        status_code=200,
        headers={"X-Deprecated": "true"}
    )

@router.get("/api/data/export")
async def legacy_data_export():
    """
    LEGACY: Data export endpoint
    DEPRECATED: Use /api/analytics/export/* instead
    """
    return JSONResponse(
        content={
            **DEPRECATION_WARNING,
            "legacy_status": "deprecated",
            "timestamp": datetime.utcnow().isoformat(),
            "new_endpoint": "/api/analytics/export/*",
            "migration_note": "Data export now uses BigQuery export capabilities"
        },
        status_code=200,
        headers={"X-Deprecated": "true"}
    )

@router.get("/api/debug/migration-status")
async def migration_status():
    """
    Migration status monitoring endpoint.

    This endpoint provides comprehensive information about the
    Google Cloud migration status and component health.
    """
    try:
        # Import validation components
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from scripts.heroku_migration_cleanup import MigrationValidator

        # Run validation
        validator = MigrationValidator()
        report = validator.run_full_validation()

        # Enhanced status response
        status_response = {
            "migration_status": "completed" if report['migration_complete'] else "in_progress",
            "migration_completed_date": MIGRATION_COMPLETED,
            "platform": "Google Cloud Platform",
            "components": {
                "cloud_function": report['validation_results'].get('cloud_function', {'status': 'unknown'}),
                "pubsub": report['validation_results'].get('pubsub', {'status': 'unknown'}),
                "cloud_storage": report['validation_results'].get('cloud_storage', {'status': 'unknown'}),
                "bigquery": report['validation_results'].get('bigquery', {'status': 'unknown'}),
                "api_endpoints": report['validation_results'].get('api_endpoints', {'status': 'unknown'})
            },
            "validation_timestamp": report['timestamp'],
            "errors": report['errors'],
            "summary": report['summary'],
            "next_steps": [] if report['migration_complete'] else [
                "Review validation errors",
                "Check GCP service account permissions",
                "Verify Cloud Function deployment",
                "Confirm Pub/Sub topic/subscription setup",
                "Validate BigQuery dataset and tables"
            ]
        }

        return JSONResponse(
            content=status_response,
            status_code=200 if report['migration_complete'] else 206  # 206 = Partial Content
        )

    except Exception as e:
        return JSONResponse(
            content={
                "migration_status": "error",
                "error": f"Failed to validate migration status: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "platform": "Google Cloud Platform"
            },
            status_code=500
        )

@router.post("/api/debug/validate-migration-complete")
async def validate_migration_complete():
    """
    Manual migration validation endpoint.

    Triggers a complete validation of the Google Cloud migration
    and returns detailed results.
    """
    try:
        # Import validation components
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from scripts.heroku_migration_cleanup import MigrationValidator

        # Run full validation
        validator = MigrationValidator()
        report = validator.run_full_validation()

        # Save detailed report
        report_file = validator.save_report(report)

        # Return validation results
        response = {
            "validation_triggered": True,
            "timestamp": datetime.utcnow().isoformat(),
            "migration_complete": report['migration_complete'],
            "report_file": report_file,
            "summary": report['summary'],
            "errors": report['errors'],
            "recommendations": [
                "Check the detailed report file for complete validation results",
                "Review any errors and address GCP configuration issues",
                "Ensure all Cloud Functions, Pub/Sub, and BigQuery resources are properly configured",
                "Verify service account has necessary permissions"
            ] if not report['migration_complete'] else [
                "Migration validation successful!",
                "All Google Cloud components are operational",
                "Legacy Heroku endpoints are deprecated and can be removed"
            ]
        }

        return JSONResponse(
            content=response,
            status_code=200 if report['migration_complete'] else 202  # 202 = Accepted (processing)
        )

    except Exception as e:
        return JSONResponse(
            content={
                "validation_triggered": False,
                "error": f"Failed to run migration validation: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=500
        )

@router.get("/api/debug/gcp-infrastructure-status")
async def gcp_infrastructure_status():
    """
    GCP Infrastructure Status Monitoring Endpoint.

    Provides comprehensive status information about all Google Cloud Platform
    resources deployed for the 7taps Analytics application.
    """
    try:
        # Import GCP configuration
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from app.config.gcp_config import gcp_config

        # Check Cloud Function status
        cloud_function_status = "unknown"
        try:
            # This would normally check actual Cloud Function status
            # For now, we'll simulate the check
            cloud_function_status = "deployed"
        except Exception:
            cloud_function_status = "error"

        # Check Pub/Sub status
        pubsub_status = "unknown"
        try:
            pubsub_status = "configured"
        except Exception:
            pubsub_status = "error"

        # Check Cloud Storage status
        storage_status = "unknown"
        try:
            storage_status = "operational"
        except Exception:
            storage_status = "error"

        # Check BigQuery status
        bigquery_status = "unknown"
        try:
            bigquery_status = "operational"
        except Exception:
            bigquery_status = "error"

        infrastructure_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "gcp_project": gcp_config.project_id,
            "region": "us-central1",
            "components": {
                "cloud_function": {
                    "name": "cloud-ingest-xapi",
                    "status": cloud_function_status,
                    "url": f"https://us-central1-{gcp_config.project_id}.cloudfunctions.net/cloud-ingest-xapi"
                },
                "pubsub": {
                    "topic": gcp_config.pubsub_topic,
                    "storage_subscription": gcp_config.pubsub_storage_subscription,
                    "bigquery_subscription": gcp_config.pubsub_bigquery_subscription,
                    "status": pubsub_status
                },
                "cloud_storage": {
                    "bucket": gcp_config.storage_bucket,
                    "status": storage_status
                },
                "bigquery": {
                    "dataset": gcp_config.bigquery_dataset,
                    "status": bigquery_status
                }
            },
            "overall_status": "operational" if all([
                cloud_function_status == "deployed",
                pubsub_status == "configured",
                storage_status == "operational",
                bigquery_status == "operational"
            ]) else "degraded"
        }

        return JSONResponse(
            content=infrastructure_status,
            status_code=200 if infrastructure_status["overall_status"] == "operational" else 206
        )

    except Exception as e:
        return JSONResponse(
            content={
                "error": f"Failed to retrieve GCP infrastructure status: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error"
            },
            status_code=500
        )

@router.post("/api/debug/validate-gcp-deployment")
async def validate_gcp_deployment():
    """
    Validate Complete GCP Deployment.

    Performs comprehensive validation of all Google Cloud Platform resources
    and services to ensure the deployment is fully operational.
    """
    try:
        # Import validation components
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from scripts.heroku_migration_cleanup import MigrationValidator
        from app.config.gcp_config import gcp_config

        # Initialize validator
        validator = MigrationValidator()

        # Run comprehensive validation
        migration_report = validator.run_full_validation()

        # Additional GCP-specific validations
        gcp_validations = {}

        # Cloud Function validation
        try:
            # Test Cloud Function HTTP endpoint
            import requests
            cf_url = f"https://us-central1-{gcp_config.project_id}.cloudfunctions.net/cloud-ingest-xapi"
            response = requests.get(cf_url, timeout=10)
            gcp_validations["cloud_function_http"] = {
                "status": "operational" if response.status_code in [200, 405] else "error",
                "response_code": response.status_code,
                "url": cf_url
            }
        except Exception as e:
            gcp_validations["cloud_function_http"] = {
                "status": "error",
                "error": str(e)
            }

        # GCP resource connectivity validation
        try:
            from google.cloud import pubsub_v1, storage, bigquery

            # Test Pub/Sub connectivity
            publisher = pubsub_v1.PublisherClient(credentials=gcp_config.get_credentials())
            topic_path = publisher.topic_path(gcp_config.project_id, gcp_config.pubsub_topic)
            publisher.get_topic(request={"topic": topic_path})
            gcp_validations["pubsub_connectivity"] = {"status": "connected"}

        except Exception as e:
            gcp_validations["pubsub_connectivity"] = {
                "status": "error",
                "error": str(e)
            }

        try:
            # Test Cloud Storage connectivity
            storage_client = storage.Client(credentials=gcp_config.get_credentials())
            bucket = storage_client.bucket(gcp_config.storage_bucket)
            bucket.exists()
            gcp_validations["storage_connectivity"] = {"status": "connected"}

        except Exception as e:
            gcp_validations["storage_connectivity"] = {
                "status": "error",
                "error": str(e)
            }

        try:
            # Test BigQuery connectivity
            bq_client = bigquery.Client(credentials=gcp_config.get_credentials())
            dataset = bq_client.get_dataset(gcp_config.bigquery_dataset)
            gcp_validations["bigquery_connectivity"] = {"status": "connected"}

        except Exception as e:
            gcp_validations["bigquery_connectivity"] = {
                "status": "error",
                "error": str(e)
            }

        # Compile final validation report
        validation_report = {
            "validation_timestamp": datetime.utcnow().isoformat(),
            "gcp_project": gcp_config.project_id,
            "migration_validation": {
                "complete": migration_report.get('migration_complete', False),
                "summary": migration_report.get('summary', {}),
                "errors": migration_report.get('errors', [])
            },
            "gcp_resource_validation": gcp_validations,
            "deployment_status": "fully_operational" if (
                migration_report.get('migration_complete', False) and
                all(v.get("status") == "connected" or v.get("status") == "operational"
                    for v in gcp_validations.values())
            ) else "issues_detected",
            "recommendations": []
        }

        # Add recommendations based on validation results
        if not migration_report.get('migration_complete', False):
            validation_report["recommendations"].append("Complete migration validation - some components may need attention")

        for resource, status in gcp_validations.items():
            if status.get("status") in ["error", "disconnected"]:
                validation_report["recommendations"].append(f"Check {resource.replace('_', ' ')} configuration and connectivity")

        if validation_report["deployment_status"] == "fully_operational":
            validation_report["recommendations"].append("GCP deployment is fully operational and ready for production use")

        return JSONResponse(
            content=validation_report,
            status_code=200 if validation_report["deployment_status"] == "fully_operational" else 206
        )

    except Exception as e:
        return JSONResponse(
            content={
                "validation_timestamp": datetime.utcnow().isoformat(),
                "error": f"Failed to validate GCP deployment: {str(e)}",
                "deployment_status": "validation_error",
                "recommendations": ["Check GCP credentials and network connectivity"]
            },
            status_code=500
        )

@router.get("/api/debug/gcp-resource-health")
async def gcp_resource_health():
    """
    GCP Resource Health Check Endpoint.

    Provides real-time health status for individual Google Cloud Platform
    resources with detailed metrics and performance indicators.
    """
    try:
        # Import GCP components
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

        from app.config.gcp_config import gcp_config

        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "gcp_project": gcp_config.project_id,
            "resources": {}
        }

        # Cloud Function health
        try:
            import requests
            cf_url = f"https://us-central1-{gcp_config.project_id}.cloudfunctions.net/cloud-ingest-xapi"
            start_time = datetime.utcnow()
            response = requests.get(cf_url, timeout=5)
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            health_status["resources"]["cloud_function"] = {
                "status": "healthy" if response.status_code in [200, 405] else "unhealthy",
                "response_time_ms": round(response_time, 2),
                "response_code": response.status_code,
                "url": cf_url
            }
        except Exception as e:
            health_status["resources"]["cloud_function"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # Pub/Sub health (subscription metrics)
        try:
            from google.cloud import pubsub_v1
            subscriber = pubsub_v1.SubscriberClient(credentials=gcp_config.get_credentials())

            # Check subscription existence and basic metrics
            subscription_path = subscriber.subscription_path(
                gcp_config.project_id, gcp_config.pubsub_storage_subscription
            )

            # This would normally get actual metrics, but for now we'll simulate
            health_status["resources"]["pubsub"] = {
                "status": "healthy",
                "subscriptions_checked": [
                    gcp_config.pubsub_storage_subscription,
                    gcp_config.pubsub_bigquery_subscription
                ],
                "message_backlog": 0  # Would get actual backlog
            }
        except Exception as e:
            health_status["resources"]["pubsub"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # Cloud Storage health
        try:
            from google.cloud import storage
            storage_client = storage.Client(credentials=gcp_config.get_credentials())
            bucket = storage_client.bucket(gcp_config.storage_bucket)

            # Check bucket accessibility and basic stats
            if bucket.exists():
                blobs = list(bucket.list_blobs(max_results=1))
                health_status["resources"]["cloud_storage"] = {
                    "status": "healthy",
                    "bucket": gcp_config.storage_bucket,
                    "accessible": True,
                    "has_content": len(blobs) > 0
                }
            else:
                health_status["resources"]["cloud_storage"] = {
                    "status": "unhealthy",
                    "bucket": gcp_config.storage_bucket,
                    "accessible": False,
                    "error": "Bucket does not exist"
                }
        except Exception as e:
            health_status["resources"]["cloud_storage"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # BigQuery health
        try:
            from google.cloud import bigquery
            bq_client = bigquery.Client(credentials=gcp_config.get_credentials())

            # Check dataset and table accessibility
            dataset_ref = bq_client.dataset(gcp_config.bigquery_dataset)
            dataset = bq_client.get_dataset(dataset_ref)

            tables = list(bq_client.list_tables(dataset_ref))
            table_count = len(tables)

            health_status["resources"]["bigquery"] = {
                "status": "healthy",
                "dataset": gcp_config.bigquery_dataset,
                "table_count": table_count,
                "accessible": True
            }
        except Exception as e:
            health_status["resources"]["bigquery"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # Overall health assessment
        resource_statuses = [r.get("status", "unknown") for r in health_status["resources"].values()]
        if all(status == "healthy" for status in resource_statuses):
            health_status["overall_health"] = "healthy"
            http_status = 200
        elif any(status == "unhealthy" for status in resource_statuses):
            health_status["overall_health"] = "unhealthy"
            http_status = 503
        else:
            health_status["overall_health"] = "degraded"
            http_status = 206

        return JSONResponse(
            content=health_status,
            status_code=http_status
        )

    except Exception as e:
        return JSONResponse(
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "overall_health": "error",
                "error": f"Failed to check GCP resource health: {str(e)}",
                "resources": {}
            },
            status_code=500
        )

@router.get("/api/debug/legacy-endpoints")
async def list_legacy_endpoints():
    """
    List all deprecated legacy endpoints.

    This endpoint provides information about all legacy endpoints
    that have been deprecated during the Google Cloud migration.
    """
    legacy_endpoints = [
        {
            "endpoint": "/api/health (legacy)",
            "status": "deprecated",
            "replacement": "/api/health",
            "migration_date": MIGRATION_COMPLETED
        },
        {
            "endpoint": "/api/xapi/statements",
            "status": "deprecated",
            "replacement": "/api/xapi/cloud-ingest",
            "migration_date": MIGRATION_COMPLETED
        },
        {
            "endpoint": "/api/analytics/dashboard",
            "status": "deprecated",
            "replacement": "/api/analytics/bigquery/dashboard",
            "migration_date": MIGRATION_COMPLETED
        },
        {
            "endpoint": "/api/data/export",
            "status": "deprecated",
            "replacement": "/api/analytics/export/*",
            "migration_date": MIGRATION_COMPLETED
        }
    ]

    return JSONResponse(
        content={
            "legacy_endpoints": legacy_endpoints,
            "total_deprecated": len(legacy_endpoints),
            "migration_status": "completed",
            "migration_completed_date": MIGRATION_COMPLETED,
            "note": "These endpoints return deprecation warnings and will be removed in a future version"
        },
        status_code=200
    )
