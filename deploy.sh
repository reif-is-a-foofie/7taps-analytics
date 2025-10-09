#!/bin/bash
# Clean deployment flow: commit -> push -> deploy to Google Cloud

set -e

echo "🚀 Clean Deploy Pipeline"
echo "========================"

# Step 1: Commit and push
echo ""
echo "📝 Step 1: Committing and pushing changes..."
./quick-commit.sh

# Step 2: Trigger build via GitHub push (automatic via Cloud Build trigger)
echo ""
echo "☁️  Step 2: Cloud Build will auto-deploy from GitHub..."
echo "⏱️  Build typically takes 3-5 minutes"
echo "📊 Monitor: https://console.cloud.google.com/cloud-build/builds?project=taps-data"

echo ""
echo "✅ Code pushed to GitHub!"
echo "🔗 Production URL: https://taps-analytics-ui-245712978112.us-central1.run.app"
echo "⌛ Wait 3-5 minutes for automatic deployment to complete"
