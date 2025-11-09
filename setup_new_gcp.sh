#!/bin/bash
# Quick setup script for new GCP project: pol-a-477603

set -e

PROJECT_ID="pol-a-477603"

# API key should be passed as first argument or environment variable
API_KEY="${1:-${GOOGLE_AI_API_KEY}}"

if [ -z "$API_KEY" ]; then
    echo "Error: API key required"
    echo "Usage: $0 <API_KEY>"
    echo "   OR: GOOGLE_AI_API_KEY=<key> $0"
    exit 1
fi

echo "Setting up Google Cloud project: $PROJECT_ID"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  containerregistry.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  --project=$PROJECT_ID

# Store API key in Secret Manager
echo ""
echo "Storing Google AI API Key..."
echo -n "$API_KEY" | gcloud secrets create google-ai-api-key \
  --project=$PROJECT_ID \
  --data-file=- 2>/dev/null || \
echo -n "$API_KEY" | gcloud secrets versions add google-ai-api-key \
  --project=$PROJECT_ID \
  --data-file=-

# Get project number for service account
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Cloud Run access
echo "Granting Cloud Run access to secret..."
gcloud secrets add-iam-policy-binding google-ai-api-key \
  --project=$PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Project ID: $PROJECT_ID"
echo "API Key: Stored in Secret Manager as 'google-ai-api-key'"
echo ""
echo "Next: Deploy your application with:"
echo "  gcloud builds submit --config cloudbuild.yaml"
