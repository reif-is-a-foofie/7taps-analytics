# New GCP Account Deployment Guide

## Problem
The original Cloud Run URL `https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/statements` cannot be recreated because:
- Cloud Run URLs include a hash (`zz2ztq5bjq`) generated from the project ID
- The original GCP account/project was deleted
- 7taps is configured to send xAPI statements to this specific URL and cannot be updated

## ⚠️ Important: Contact 7taps First

**Before spending time on complex solutions, contact 7taps support** to see if they can update the webhook URL. Many webhook systems allow URL updates, and this would be the simplest solution.

If they absolutely cannot update it, proceed with the solutions below.

## ⚠️ Critical Technical Limitation

**Reality:** You **cannot recreate the exact `.run.app` URL** because:
- Google controls DNS for `.run.app` domain
- The hash `zz2ztq5bjq` is deterministic based on the deleted project ID
- You cannot create DNS records for Google-owned domains

**If 7taps is hardcoded to that exact URL and cannot update it**, your options are:
1. **Contact Google Support** - Ask about project restoration (unlikely)
2. **Try project ID hash matching** - Very unlikely to work
3. **Escalate with 7taps** - They may have admin tools to update webhooks

## Solution: Cloud Load Balancer (If Custom Domain Works)

Use a **Global HTTP(S) Load Balancer** with a custom domain to preserve the exact URL pattern.

**Steps:**
1. Deploy your app to new GCP account
2. Create a Cloud Load Balancer
3. Configure a custom domain that matches the old URL pattern
4. Route traffic to your new Cloud Run service

**Requirements:**
- You need to own/control a domain (or subdomain)
- Set up DNS to point to the load balancer IP

### Load Balancer Setup Commands

```bash
# 1. Reserve a static IP
gcloud compute addresses create taps-analytics-lb-ip \
  --global \
  --project=$PROJECT_ID

# 2. Get the IP address
LB_IP=$(gcloud compute addresses describe taps-analytics-lb-ip \
  --global \
  --format="value(address)")

# 3. Create backend service pointing to Cloud Run
gcloud compute backend-services create taps-analytics-backend \
  --global \
  --load-balancing-scheme=EXTERNAL

# 4. Add Cloud Run NEG (Network Endpoint Group)
gcloud compute network-endpoint-groups create taps-analytics-neg \
  --region=us-central1 \
  --network-endpoint-type=serverless \
  --cloud-run-service=taps-analytics-ui

# 5. Add NEG to backend service
gcloud compute backend-services add-backend taps-analytics-backend \
  --global \
  --network-endpoint-group=taps-analytics-neg \
  --network-endpoint-group-region=us-central1

# 6. Create URL map
gcloud compute url-maps create taps-analytics-url-map \
  --default-service=taps-analytics-backend

# 7. Create HTTPS proxy (requires SSL certificate)
gcloud compute target-https-proxies create taps-analytics-https-proxy \
  --url-map=taps-analytics-url-map \
  --ssl-certificates=YOUR_SSL_CERT_NAME

# 8. Create forwarding rule
gcloud compute forwarding-rules create taps-analytics-forwarding-rule \
  --global \
  --target-https-proxy=taps-analytics-https-proxy \
  --address=taps-analytics-lb-ip \
  --ports=443

# 9. Configure DNS
# Point your domain (e.g., taps-analytics-ui-zz2ztq5bjq-uc.a.run.app) 
# to the load balancer IP: $LB_IP
```

**Note:** This requires SSL certificate setup. See [GCP Load Balancer docs](https://cloud.google.com/load-balancing/docs/ssl-certificates) for details.

## Alternative: Try Project ID Hash Matching

**Experimental approach:** Try different project IDs until you find one that generates a similar hash.

```bash
# Script to test project ID hashes
for project_id in taps-analytics taps-analytics-ui taps-analytics-prod; do
  echo "Testing: $project_id"
  # Deploy and check URL hash
done
```

**Note:** This is unlikely to work but worth trying if you have time.

## Fallback: Proxy Service

If you can't use a load balancer, deploy the proxy service (see `proxy_service/` directory) and ask 7taps to update their webhook URL to the new proxy URL.

## Deployment Steps

### 1. Set Up New GCP Project

```bash
# Authenticate
gcloud auth login

# Create new project (or use existing)
gcloud projects create pol-a-477603 --name="7taps Analytics" || echo "Project may already exist"

# Set as active project
gcloud config set project pol-a-477603

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  containerregistry.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### 2. Update Configuration

Update `app/config.py` with new project ID:

```python
GCP_PROJECT_ID: str = "pol-a-477603"  # Updated
GCP_BIGQUERY_DATASET: str = "taps_data"
GCP_LOCATION: str = "us-central1"
```

### 3. Deploy to Cloud Run

```bash
# Build and deploy
gcloud builds submit --config cloudbuild.yaml

# Or use the deploy script
./deploy.sh
```

### 4. Get New Cloud Run URL

```bash
gcloud run services describe taps-analytics-ui \
  --region=us-central1 \
  --format="value(status.url)"
```

### 5. Set Up Domain Mapping (Option 1)

If you have a domain, map it:

```bash
# Create domain mapping
gcloud run domain-mappings create \
  --service=taps-analytics-ui \
  --domain=taps-analytics-ui-zz2ztq5bjq-uc.a.run.app \
  --region=us-central1

# Note: This requires DNS configuration
```

### 6. Verify Endpoint

Test the `/statements` endpoint:

```bash
curl -X PUT https://NEW-URL/statements \
  -H "Content-Type: application/json" \
  -u "7taps.team:PracticeofLife" \
  -d '{"test": "statement"}'
```

## Required Environment Variables

Set these in Cloud Run:

```bash
gcloud run services update taps-analytics-ui \
  --region=us-central1 \
  --set-env-vars="GCP_PROJECT_ID=pol-a-477603" \
  --set-env-vars="GCP_BIGQUERY_DATASET=taps_data" \
  --set-env-vars="GCP_LOCATION=us-central1"
```

## Secrets Setup

If using secrets (e.g., `GOOGLE_AI_API_KEY`):

```bash
# Create secret
echo -n "your-api-key" | gcloud secrets create google-ai-api-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding google-ai-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Quick Reference

**Current Endpoint:** `https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/statements`
**Credentials:** `7taps.team:PracticeofLife`
**Methods:** PUT, POST
**Content-Type:** `application/json`

## Next Steps After Deployment

1. Test endpoint with sample xAPI statement
2. Verify BigQuery data ingestion
3. Check Pub/Sub topic is receiving messages
4. Update 7taps webhook configuration OR set up domain mapping
5. Monitor Cloud Run logs for incoming requests

