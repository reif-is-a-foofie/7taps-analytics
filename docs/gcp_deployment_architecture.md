# Google Cloud Deployment Architecture

## Overview

The 7taps Analytics platform is deployed on Google Cloud Platform using a serverless, event-driven architecture that provides scalability, cost-efficiency, and high availability.

## Architecture Components

### 1. **Cloud Run Service** (UI Server)
- **Service**: `7taps-analytics-ui`
- **Purpose**: Serves the FastAPI application and all UI components
- **Resources**: 1 CPU, 2GB RAM, 0-10 instances
- **Endpoints**:
  - Dashboard: `/`
  - Chat Interface: `/chat`
  - Data Explorer: `/explorer`
  - API Documentation: `/api/docs`
  - BigQuery Dashboard: `/ui/bigquery-dashboard`
  - Health Check: `/api/health`

### 2. **Cloud Functions** (Data Ingestion)
- **Function**: `cloud-ingest-xapi`
- **Purpose**: HTTP-triggered ingestion of xAPI statements
- **Runtime**: Python 3.9
- **Resources**: 512MB RAM, 60s timeout, 100 max instances

### 3. **Pub/Sub** (Event Streaming)
- **Topic**: `xapi-ingestion-topic`
- **Subscriptions**:
  - `xapi-storage-subscriber`: Archives raw data to Cloud Storage
  - `xapi-bigquery-subscriber`: Transforms and loads data to BigQuery

### 4. **Cloud Storage** (Raw Data Archive)
- **Bucket**: `taps-data-raw-xapi`
- **Purpose**: Long-term storage of raw xAPI statements
- **Lifecycle**: 365-day retention policy

### 5. **BigQuery** (Analytics Data Warehouse)
- **Dataset**: `taps_data`
- **Tables**:
  - `users`: User profiles and information
  - `lessons`: Lesson definitions and metadata
  - `questions`: Question definitions
  - `user_responses`: User responses to questions
  - `user_activities`: Learning activities and progress
  - `xapi_events`: Raw xAPI statements for advanced analytics

## Data Flow

```
xAPI Statements → Cloud Function → Pub/Sub Topic
                                        ↓
                              ┌─────────────────┐
                              │                 │
                              ▼                 ▼
                    Cloud Storage         BigQuery
                    (Raw Archive)      (Analytics)
                              │                 │
                              └─────────────────┘
                                        ↓
                              Cloud Run Service
                              (UI & API)
```

## Deployment Status

### ✅ Completed Components
- **gc01**: Cloud Function Ingestion
- **gc02**: Pub/Sub Storage Subscriber  
- **gc03**: BigQuery Schema Migration
- **gc04**: Analytics Dashboard Integration
- **gc05**: Migration Cleanup & Validation
- **gc06**: Google Cloud Infrastructure Deployment

### 🔄 In Progress
- **gc07**: UI Cloud Run Deployment

## Required GCP Resources

### APIs Enabled
- `cloudfunctions.googleapis.com`
- `pubsub.googleapis.com`
- `storage.googleapis.com`
- `bigquery.googleapis.com`
- `run.googleapis.com`
- `cloudbuild.googleapis.com`
- `containerregistry.googleapis.com`
- `iam.googleapis.com`
- `logging.googleapis.com`
- `monitoring.googleapis.com`

### Service Account Roles
- `roles/cloudfunctions.invoker`
- `roles/pubsub.publisher`
- `roles/pubsub.subscriber`
- `roles/storage.objectAdmin`
- `roles/bigquery.dataEditor`
- `roles/bigquery.jobUser`
- `roles/run.invoker`
- `roles/run.developer`
- `roles/cloudbuild.builds.builder`
- `roles/storage.objectViewer`
- `roles/logging.logWriter`
- `roles/monitoring.metricWriter`

## Environment Variables

### Cloud Run Service
```bash
API_BASE_URL=""  # Empty for relative URLs
DATABASE_TERMINAL_URL="https://your-sqlpad-instance.run.app"
GOOGLE_CLOUD_PROJECT="taps-data"
GCP_REGION="us-central1"
DATABASE_URL="from_secret"  # BigQuery connection
REDIS_URL="from_secret"     # If using Redis
```

### Cloud Function
```bash
GCP_PROJECT_ID="taps-data"
PUBSUB_TOPIC="xapi-ingestion-topic"
STORAGE_BUCKET="taps-data-raw-xapi"
```

## Deployment Commands

### Deploy UI to Cloud Run
```bash
python scripts/deploy_cloud_run_ui.py
```

### Deploy Cloud Function
```bash
gcloud functions deploy cloud-ingest-xapi \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --source . \
  --entry-point cloud_ingest_xapi
```

### Set up Infrastructure
```bash
python scripts/setup_gcp_resources.py
```

## Cost Optimization

- **Cloud Run**: Pay-per-request with 0 minimum instances
- **Cloud Functions**: Pay-per-invocation
- **Pub/Sub**: Pay-per-message
- **BigQuery**: Pay-per-query with partitioned tables
- **Cloud Storage**: Pay-per-GB with lifecycle policies

## Monitoring & Health Checks

### Endpoints
- `/api/health`: Application health
- `/api/debug/gcp-infrastructure-status`: GCP resource status
- `/api/debug/gcp-resource-health`: Resource health check
- `/api/debug/validate-gcp-deployment`: Deployment validation

### Alerts
- Cloud Function error rate > 5%
- Pub/Sub message backlog > 1000 messages
- Cloud Run service errors
- BigQuery query failures

## Security

- Service account authentication
- IAM role-based access control
- HTTPS-only communication
- Environment variable secrets management
- VPC network isolation (if needed)

## Next Steps

1. **Deploy Cloud Run Service**: Run the deployment script
2. **Configure Environment Variables**: Set up secrets and configuration
3. **Test UI Endpoints**: Verify all functionality works
4. **Set up Monitoring**: Configure alerts and dashboards
5. **Performance Testing**: Load test the complete system
6. **Documentation**: Update user guides and API docs
