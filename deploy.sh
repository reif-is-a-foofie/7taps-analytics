#!/bin/bash
# Clean deployment flow: commit -> push -> deploy to Google Cloud

set -e

echo "🚀 Clean Deploy Pipeline"
echo "========================"

# Step 1: Commit
echo ""
echo "📝 Step 1: Committing changes..."
./quick-commit.sh

# Step 2: Deploy via Cloud Build
echo ""
echo "☁️  Step 2: Deploying to Google Cloud..."
gcloud builds submit --config cloudbuild.yaml .

echo ""
echo "✅ Deployment complete!"
echo "🔗 URL: https://taps-analytics-ui-245712978112.us-central1.run.app"
