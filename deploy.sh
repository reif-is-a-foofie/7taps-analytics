#!/bin/bash

# Rapid Cloud Run deployment for enhanced safety system
echo "🚀 Deploying Enhanced Safety System to Cloud Run..."

# Check if .env file exists and source it
if [ -f .env ]; then
    echo "📋 Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Deploy using Cloud Run with source-based deployment
gcloud run deploy safety-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="$GEMINI_API_KEY" \
  --set-env-vars GEMINI_BASE_URL="$GEMINI_BASE_URL" \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10

echo "✅ Deployment complete!"
echo "🔗 Your enhanced safety API is now live on Cloud Run"
echo "📊 Access the UI at your deployed URL + /static/safety-words.html"