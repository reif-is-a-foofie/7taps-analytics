# 🚀 7taps Analytics — Deployment Guide

This project now targets a single production footprint: Google Cloud Run
backed by BigQuery, Pub/Sub, and Redis-compatible caching. Legacy
instructions for Heroku, Railway, and direct PostgreSQL access have been
retired along with the ETL/normalization stack.

## Prerequisites

- `gcloud` CLI authenticated to the target project (`taps-data`).
- A BigQuery dataset containing the analytics tables (default
  `taps_data`).
- Optional: Redis (MemoryStore or compatible) for analytics caching. The
  ingestion pipeline now publishes directly to Pub/Sub and no longer
  requires Redis Streams.
- Environment variables supplied via Cloud Build/Run:
  - `GCP_PROJECT_ID`, `GCP_BIGQUERY_DATASET`, `GCP_LOCATION`
  - `REDIS_URL` (only if enabling BigQuery result caching)
  - `SEVENTAPS_*` secrets for webhook verification if ingesting live data.

## Deploy

1. Build and deploy with the provided Cloud Build pipeline:
   ```bash
   gcloud builds submit --config cloudbuild.yaml .
   ```
2. Cloud Build runs the test gate, builds the container, and deploys the
   image to Cloud Run service `taps-analytics-ui` in `us-central1`.
3. After the revision is active, verify the public URL printed at the end
   of the build (e.g. `https://taps-analytics-ui-<project>.us-central1.run.app`).

## Post-deploy Checklist

- `GET /health` and `GET /api/debug/cloud-run-health` return `healthy`.
- `GET /api/bigquery/test` shows dataset connectivity.
- `GET /api/cost` lists cost endpoints, and `/api/cost/current-usage`
  returns metrics.
- Optional ingestion smoke test:
  ```bash
  curl -X POST "$SERVICE_URL/api/xapi/ingest" \
       -H 'Content-Type: application/json' \
       -d '{"actor": {"name": "smoke"}, "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"}, "object": {"id": "http://example.com/activity"}}'
  ```

The container no longer depends on local PostgreSQL or Learning Locker.
If you need historic exports, query BigQuery directly.
