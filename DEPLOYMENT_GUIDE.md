# Clean Deployment Guide

## Overview
Deployment flow: **Commit → Push → Auto-Deploy to Google Cloud**

## Quick Deploy
```bash
./deploy.sh
```

This script:
1. Commits all changes via `quick-commit.sh`
2. Pushes to GitHub main branch
3. Triggers automatic Cloud Build deployment (3-5 minutes)

## Production URL
https://taps-analytics-ui-245712978112.us-central1.run.app

## Manual Deployment Setup

### One-Time: Create Cloud Build Trigger

**Web Console (Recommended):**
1. Go to: https://console.cloud.google.com/cloud-build/triggers?project=taps-data
2. Click "CREATE TRIGGER"
3. Configure:
   - **Name**: `taps-analytics-deploy`
   - **Region**: `us-central1`
   - **Event**: Push to branch
   - **Repository**: Connect `reif-is-a-foofie/7taps-analytics`
   - **Branch**: `^main$`
   - **Configuration**: Cloud Build configuration file
   - **Location**: `cloudbuild.yaml`
4. Click "CREATE"

**CLI Alternative:**
```bash
# Note: Requires GitHub App connected to GCP project
gcloud builds triggers create github \
  --name="taps-analytics-deploy" \
  --repo-name="7taps-analytics" \
  --repo-owner="reif-is-a-foofie" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"
```

### Monitor Deployments
https://console.cloud.google.com/cloud-build/builds?project=taps-data

## Deployment Configuration

### Cloud Build (`cloudbuild.yaml`)
- Builds Docker image: `gcr.io/taps-data/taps-analytics-ui`
- Deploys to Cloud Run service: `taps-analytics-ui`
- Region: `us-central1`
- Resources: 2 CPU, 2Gi memory
- Timeout: 300s
- Max instances: 10

### Commit Script (`quick-commit.sh`)
- Runs pre-deployment tests
- Auto-generates commit messages
- Pushes to main branch

## Troubleshooting

### Build Not Triggering
1. Check trigger exists: https://console.cloud.google.com/cloud-build/triggers
2. Verify GitHub connection
3. Check build history for errors

### Build Failing
1. Monitor logs: https://console.cloud.google.com/cloud-build/builds
2. Check `cloudbuild.yaml` syntax
3. Verify GCP permissions

### Deployment Issues
```bash
# Check service status
gcloud run services describe taps-analytics-ui --region us-central1

# View logs
gcloud run services logs read taps-analytics-ui --region us-central1
```

## Architecture

### Cloud Run Services
- **taps-analytics-ui** (main app)
- **ai-analysis-service** (AI content analysis)
- **analytics** (legacy)
- **liahona-api** (legacy)
- **safety-api** (legacy)

### Build Flow
1. Push to GitHub main branch
2. Cloud Build trigger activated
3. Docker image built with caching
4. Image pushed to Container Registry
5. Cloud Run service updated
6. Traffic switched to new revision
7. Public access configured via IAM

## Clean Architecture Benefits
- ✅ Single deployment script
- ✅ Automatic builds on push
- ✅ Fast builds with caching (E2_HIGHCPU_8)
- ✅ Pre-deployment testing
- ✅ No manual GCP commands needed

