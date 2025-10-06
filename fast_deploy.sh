#!/bin/bash
# Fast deployment with post-deploy E2E testing

set -e

echo "🚀 Fast Deploy with Post-Deploy E2E Testing"
echo "============================================"

# Configuration
PROJECT_URL="https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"
TIMEOUT=300  # 5 minutes for deployment

echo "📦 Starting deployment..."
echo "🌐 Target URL: $PROJECT_URL"

# Start deployment in background
echo "🚀 Deploying to Cloud Run..."
gcloud builds submit --config cloudbuild.yaml . --quiet &
DEPLOY_PID=$!

# Wait for deployment to complete
echo "⏳ Waiting for deployment (timeout: ${TIMEOUT}s)..."
if ! wait $DEPLOY_PID; then
    echo "❌ Deployment failed!"
    exit 1
fi

echo "✅ Deployment completed!"
echo "🧪 Running post-deploy E2E tests..."

# Run post-deploy tests
if python3 test_post_deploy_e2e.py; then
    echo "🎉 All E2E tests passed! Deployment successful."
else
    echo "❌ E2E tests failed! Deployment has issues."
    exit 1
fi

echo "🔗 Live URL: $PROJECT_URL"
echo "📊 Data Explorer: $PROJECT_URL/ui/data-explorer"
