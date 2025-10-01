#!/bin/bash

echo "🚀 Deploying ETL fix to Google Cloud Run..."

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   curl https://sdk.cloud.google.com | bash"
    echo "   exec -l $SHELL"
    echo "   gcloud init"
    exit 1
fi

# Deploy using fast Cloud Run method
echo "📦 Building and deploying (fast method)..."
gcloud run deploy taps-analytics-ui \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --quiet

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🔍 Check the data explorer at: https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app/ui/data-explorer"
    echo "📊 ETL errors should now be resolved"
else
    echo "❌ Deployment failed. Check the logs above."
    exit 1
fi
