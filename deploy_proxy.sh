#!/bin/bash
# Deploy proxy service to preserve old URL

set -e

PROJECT_ID="${GCP_PROJECT_ID:-taps-analytics-new}"
REGION="${GCP_REGION:-us-central1}"
BACKEND_URL="${BACKEND_URL:-}"  # Set this to your new Cloud Run URL

if [ -z "$BACKEND_URL" ]; then
    echo "Error: BACKEND_URL must be set to your new Cloud Run service URL"
    echo "Example: export BACKEND_URL=https://taps-analytics-ui-NEWHASH-uc.a.run.app"
    exit 1
fi

echo "Deploying proxy service..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Backend: $BACKEND_URL"

# Build and deploy proxy service
gcloud builds submit \
  --project="$PROJECT_ID" \
  --config=proxy_service/cloudbuild.yaml \
  proxy_service/

# Deploy to Cloud Run
gcloud run deploy taps-analytics-ui-proxy \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --source=proxy_service/ \
  --allow-unauthenticated \
  --set-env-vars="BACKEND_URL=$BACKEND_URL" \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=10 \
  --timeout=300

# Get the proxy URL
PROXY_URL=$(gcloud run services describe taps-analytics-ui-proxy \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(status.url)")

echo ""
echo "✅ Proxy deployed!"
echo "Proxy URL: $PROXY_URL"
echo ""
echo "If this matches your old URL pattern, you're done!"
echo "Otherwise, you may need to use Cloud Load Balancer for exact URL matching."

