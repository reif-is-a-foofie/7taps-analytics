#!/bin/bash
# Store Google AI API Key in Google Cloud Secret Manager

set -e

# API key must be provided as first argument or environment variable
API_KEY="${1:-${GOOGLE_AI_API_KEY}}"
PROJECT_ID="${GCP_PROJECT_ID:-pol-a-477603}"
SECRET_NAME="google-ai-api-key"

if [ -z "$API_KEY" ]; then
    echo "Error: API key required"
    echo "Usage: $0 <API_KEY>"
    echo "   OR: GOOGLE_AI_API_KEY=<key> $0"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID not set and no default project configured"
    echo "Please set GCP_PROJECT_ID or run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Storing Google AI API Key in Secret Manager..."
echo "Project: $PROJECT_ID"
echo "Secret: $SECRET_NAME"

# Enable Secret Manager API if not already enabled
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" 2>/dev/null || true

# Check if secret already exists
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "Secret already exists. Adding new version..."
    echo -n "$API_KEY" | gcloud secrets versions add "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=-
else
    echo "Creating new secret..."
    echo -n "$API_KEY" | gcloud secrets create "$SECRET_NAME" \
        --project="$PROJECT_ID" \
        --data-file=-
fi

# Get project number for service account
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

# Grant Cloud Run service account access to the secret
echo "Granting Cloud Run access to secret..."
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    || echo "Warning: Could not grant IAM access. You may need to do this manually."

echo ""
echo "✅ Secret stored successfully!"
echo ""
echo "Next steps:"
echo "1. Update Cloud Run service to use the secret:"
echo "   gcloud run services update taps-analytics-ui \\"
echo "     --region=us-central1 \\"
echo "     --update-secrets=GOOGLE_AI_API_KEY=$SECRET_NAME:latest"
echo ""
echo "2. Or it will be automatically configured on next deployment via cloudbuild.yaml"

