#!/bin/bash
# Fast deployment script for 7taps Analytics
# Deploys directly to Cloud Run in ~30 seconds

set -e

echo "🚀 Fast deploying to Cloud Run..."

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Source gcloud path if available
if [ -f "/Users/reif/google-cloud-sdk/path.zsh.inc" ]; then
    source /Users/reif/google-cloud-sdk/path.zsh.inc
fi

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   curl https://sdk.cloud.google.com | bash"
    echo "   exec -l $SHELL"
    echo "   gcloud init"
    exit 1
fi

# Deploy directly to Cloud Run
gcloud run deploy taps-analytics-ui \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --quiet

echo "✅ Deployment complete!"
echo "🌐 Service URL: https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
