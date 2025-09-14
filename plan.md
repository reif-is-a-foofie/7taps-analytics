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

## Agent Activation Protocol

When a user says "go" or "start" to any agent:

1. **Read this plan.md** to understand current project state
2. **CHECK FOR RESUMABLE WORK** - Look for contracts you can resume:
   - Use `find_resumable_contracts()` to find partially completed work
   - Resume from last heartbeat if available
   - Continue from last milestone
3. **Scan `project_management/contracts/`** for new contracts assigned to your agent role
4. **Identify highest priority contract** based on:
   - Resumable work (highest priority)
   - Status: "pending" > "in_progress" > "awaiting_verification"
   - Dependencies: Ensure prerequisites are complete
   - Module sequence: Follow gc.01 → gc.02 → gc.03 order
5. **Begin work immediately** on the identified contract
6. **Send heartbeat every 15 minutes** with progress updates
7. **Report progress** via JSON to `/api/debug/test-report`

**Contract Discovery**: Each agent should proactively find their assigned contracts and work on the highest priority one.

**Heartbeat System**: Agents must send heartbeats every 15 minutes with:
- Files modified
- Code metrics (lines of code, functions implemented, endpoints created)
- Progress percentage
- Next milestone
- Current status
- Blocking issues
- Completion estimate (based on code metrics, not time)
- Last activity

This allows seamless resumption of partially completed work based on concrete code progress.

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

### gc.06 Google Cloud Infrastructure Deployment (✅ COMPLETED)

**Files**
- `scripts/deploy_gcp_infrastructure.sh`
- `scripts/setup_gcp_resources.py`
- `config/gcp_deployment_config.json`
- `orchestrator_contracts/gc06_google_cloud_deployment.json`

**Steps**
1. ✅ Set up GCP project and enable required APIs
2. ✅ Deploy Cloud Function for xAPI ingestion
3. ✅ Create Pub/Sub topics and subscriptions
4. ✅ Set up Cloud Storage buckets for raw data
5. ✅ Create BigQuery datasets and tables
6. ✅ Configure IAM permissions and service accounts
7. ✅ Add deployment monitoring and health check endpoints
8. ✅ Migrate existing data from Heroku PostgreSQL to BigQuery

**Tests**
- `python test_gcp_deployment.py`
- `python test_monitoring_endpoints.py`
- GCP infrastructure status via `/api/debug/gcp-infrastructure-status`

### gc.07 UI Cloud Run Deployment (🔄 IN PROGRESS)

**Files**
- `scripts/deploy_cloud_run_ui.py`
- `config/Dockerfile`
- `app/main.py`
- `templates/`
- `app/ui/`
- `orchestrator_contracts/gc07_ui_cloud_run_deployment.json`

**Steps**
1. ✅ Create Cloud Run deployment script for UI
2. Deploy FastAPI application to Cloud Run
3. Configure environment variables for GCP
4. Verify UI endpoints are accessible

**Tests**
- `python scripts/deploy_cloud_run_ui.py`
- UI endpoints: `/`, `/chat`, `/explorer`, `/api/docs`
- Health check via `/api/health`

---

### Contract Creation

Use `project_management/contracts/contract_schema.json` for all new module contracts.
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

### Deployment Process

**For New Agents - Complete GCP Deployment Steps:**

1. **Install Dependencies**
   ```bash
   pip3 install google-cloud-pubsub google-cloud-storage google-cloud-bigquery
   pip3 install google-auth google-auth-oauthlib google-auth-httplib2
   pip3 install google-api-python-client google-cloud-resource-manager
   ```

2. **Authenticate with GCP**
   ```bash
   gcloud auth activate-service-account --key-file=google-cloud-key.json
   gcloud config set project taps-data
   ```

3. **Deploy Infrastructure**
   ```bash
   python3 scripts/deploy_gcp_python_only.py
   ```

4. **Deploy Cloud Function**
   ```bash
   gcloud functions deploy cloud-ingest-xapi \
     --runtime python39 \
     --trigger-http \
     --allow-unauthenticated \
     --source app/api \
     --entry-point cloud_ingest_xapi \
     --memory 512MB \
     --timeout 60s \
     --max-instances 100 \
     --set-env-vars GCP_PROJECT_ID=taps-data,PUBSUB_TOPIC=xapi-ingestion-topic,STORAGE_BUCKET=taps-data-raw-xapi \
     --no-gen2
   ```

5. **Test Deployment**
   ```bash
   # Test xAPI ingestion
   curl -X POST https://us-central1-taps-data.cloudfunctions.net/cloud-ingest-xapi \
     -H "Content-Type: application/json" \
     -d '{"actor": {"mbox": "mailto:test@example.com"}, "verb": {"id": "http://adlnet.gov/expapi/verbs/experienced"}, "object": {"id": "http://example.com/activity"}}'
   ```

**Deployment URLs:**
- **Cloud Function**: `https://us-central1-taps-data.cloudfunctions.net/cloud-ingest-xapi`
- **GCP Console**: `https://console.cloud.google.com/functions/list?project=taps-data`
- **BigQuery**: `https://console.cloud.google.com/bigquery?project=taps-data`

**Required Files:**
- `google-cloud-key.json` (service account key - NEVER commit)
- `app/api/main.py` (Cloud Function entry point)
- `app/api/requirements.txt` (Cloud Function dependencies)
- `app/api/cloud_function_ingestion.py` (main function code)

**Verification Checklist:**
- ✅ GCP APIs enabled (Cloud Functions, Pub/Sub, Storage, BigQuery)
- ✅ Pub/Sub topic `xapi-ingestion-topic` exists
- ✅ Cloud Storage bucket `taps-data-raw-xapi` exists
- ✅ BigQuery dataset `taps_data` with 6 tables
- ✅ Cloud Function deployed and responding
- ✅ Test xAPI statement successfully published to Pub/Sub

