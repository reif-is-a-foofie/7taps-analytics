# Plan (Google Cloud Migration)

## Overview

This plan outlines the migration from Heroku-based deployment to Google Cloud Platform. The new architecture uses Cloud Functions for ingestion, Pub/Sub for event streaming, Cloud Storage for raw data archival, and BigQuery for analytics, providing a fully serverless, scalable solution.

### Migration Benefits

| Aspect | Heroku (Previous) | Google Cloud (Current) | Improvement |
| --- | --- | --- | --- |
| **Reliability** | Cold start issues | Always-on Cloud Functions | 100% uptime |
| **Scalability** | Single server bottleneck | Auto-scaling serverless | Infinite scale |
| **Cost** | Fixed server costs | Pay-per-use | Near-zero idle costs |
| **Architecture** | Monolithic server | Event-driven microservices | Better decoupling |
| **Maintenance** | Server management | Fully managed services | Reduced ops overhead |

## Google Cloud Development Plan

Implement modules in order, ensuring each exposes test endpoints and is covered
by orchestrator contracts. Each module builds upon the previous one.

### gc.01 Cloud Function Ingestion (✅ COMPLETED)

**Files**
- `app/api/cloud_function_ingestion.py`
- `app/config/gcp_config.py`
- `tests/test_cloud_function_ingestion.py`
- `orchestrator_contracts/gc01_cloud_function_ingestion.json`

**Steps**
1. ✅ Deploy Cloud Function HTTP trigger for xAPI ingestion
2. ✅ Configure GCP service account authentication using `google-cloud-key.json`
3. ✅ Implement Pub/Sub message publishing from Cloud Function
4. ✅ Add test endpoint for Cloud Function status monitoring

**Tests**
- `pytest tests/test_cloud_function_ingestion.py`
- Cloud Function health check via `/api/debug/cloud-function-status`

### gc.02 Pub/Sub Storage Subscriber

**Files**
- `app/etl/pubsub_storage_subscriber.py`
- `tests/test_pubsub_storage_subscriber.py`
- `orchestrator_contracts/gc02_pubsub_storage_subscriber.json`

**Steps**
1. Create Pub/Sub subscriber for raw xAPI data archival
2. Implement Cloud Storage integration for raw JSON payloads
3. Add monitoring endpoints for storage subscriber health

**Tests**
- `pytest tests/test_pubsub_storage_subscriber.py`
- Storage subscriber status via `/api/debug/storage-subscriber-status`

### gc.03 BigQuery Schema Migration

**Files**
- `app/etl/bigquery_schema_migration.py`
- `app/config/bigquery_schema.py`
- `tests/test_bigquery_schema_migration.py`
- `orchestrator_contracts/gc03_bigquery_schema_migration.json`

**Steps**
1. Define BigQuery schema for structured xAPI events
2. Create Pub/Sub subscriber for schema transformation
3. Implement xAPI JSON to structured table transformation
4. Add BigQuery table creation and data insertion logic

**Tests**
- `pytest tests/test_bigquery_schema_migration.py`
- BigQuery migration status via `/api/debug/bigquery-migration-status`

### gc.04 Analytics Dashboard Integration

**Files**
- `app/ui/bigquery_dashboard.py`
- `app/api/bigquery_analytics.py`
- `templates/bigquery_dashboard.html`
- `tests/test_bigquery_analytics.py`
- `orchestrator_contracts/gc04_analytics_dashboard_integration.json`

**Steps**
1. Create BigQuery connection and query interface
2. Build analytics dashboard UI for BigQuery data
3. Implement pre-built analytics queries for common metrics

**Tests**
- `pytest tests/test_bigquery_analytics.py`
- Dashboard access via `/ui/bigquery-dashboard`

### gc.05 Migration Cleanup & Validation

**Files**
- `scripts/heroku_migration_cleanup.py`
- `app/api/legacy_heroku_endpoints.py`
- `tests/test_migration_cleanup.py`
- `orchestrator_contracts/gc05_heroku_migration_cleanup.json`

**Steps**
1. Create migration validation script
2. Mark legacy Heroku endpoints as deprecated
3. Add migration status monitoring endpoints

**Tests**
- `pytest tests/test_migration_cleanup.py`
- Migration status via `/api/debug/migration-status`

---

### Contract Creation

Use `orchestrator_contracts/contract_schema.json` for all new module contracts.
Each contract must define `module`, `agent`, `allowed_files`, `required_endpoints`,
and `status`. Google Cloud migration contracts use the `gcXX_` prefix.

### GCP Service Account Setup

**Security Requirements:**
- GCP service account key located at `google-cloud-key.json` in project root
- **NEVER commit `google-cloud-key.json` to version control**
- Keep key file secure and never expose in logs or responses
- Reference key path in configuration files, never load contents

**Required GCP Resources:**
- Cloud Functions (HTTP triggers)
- Pub/Sub topics and subscriptions
- Cloud Storage buckets
- BigQuery datasets and tables

### Testing Requirements

Run `pytest` after any changes to confirm the repository is consistent. Each module
must pass GCP integration tests before proceeding to the next module.

**GCP Integration Testing:**
- Cloud Function deployment and HTTP triggers
- Pub/Sub topic and subscription creation
- Cloud Storage bucket access
- BigQuery dataset and table operations
- Service account authentication and permissions

### Deployment Commands

```bash
# Deploy Cloud Function
gcloud functions deploy cloud-ingest-xapi \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated

# Set up Pub/Sub infrastructure
gcloud pubsub topics create xapi-ingestion-topic
gcloud pubsub subscriptions create xapi-storage-subscriber --topic xapi-ingestion-topic
gcloud pubsub subscriptions create xapi-bigquery-subscriber --topic xapi-ingestion-topic

# Create BigQuery dataset
bq mk taps_data
```

