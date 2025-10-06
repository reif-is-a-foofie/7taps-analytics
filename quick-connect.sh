#!/bin/bash

# Quick GitHub to Cloud Build connection script
echo "🚀 Quick GitHub to Cloud Build Connection"
echo "=========================================="

PROJECT_ID="taps-data"
REPO_OWNER="reif-is-a-foofie"
REPO_NAME="7taps-analytics"

echo "📋 Project: $PROJECT_ID"
echo "📋 Repository: $REPO_OWNER/$REPO_NAME"
echo ""

# Step 1: Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable artifactregistry.googleapis.com --project=$PROJECT_ID
echo "✅ APIs enabled"
echo ""

# Step 2: Install GitHub App (interactive)
echo "📱 Installing Google Cloud Build GitHub App..."
echo "🔗 Please visit: https://github.com/apps/google-cloud-build/installations/new"
echo ""
echo "Steps:"
echo "1. Select 'reif-is-a-foofie' account"
echo "2. Choose 'Selected repositories'" 
echo "3. Select '7taps-analytics'"
echo "4. Click 'Install'"
echo ""

# Try to open browser
if command -v open &> /dev/null; then
    open "https://github.com/apps/google-cloud-build/installations/new"
    echo "🌐 Opened browser automatically"
elif command -v xdg-open &> /dev/null; then
    xdg-open "https://github.com/apps/google-cloud-build/installations/new"
    echo "🌐 Opened browser automatically"
fi

read -p "Press Enter after completing the GitHub App installation..."

# Step 3: Create production trigger
echo ""
echo "🎯 Creating production trigger..."
gcloud builds triggers create github \
  --repo-owner=$REPO_OWNER \
  --repo-name=$REPO_NAME \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name="safety-api-production" \
  --description="Deploy safety-api to production on main branch push" \
  --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "✅ Production trigger created"
else
    echo "❌ Failed to create production trigger"
fi

# Step 4: Create staging trigger
echo ""
echo "🎭 Creating staging trigger..."
gcloud builds triggers create github \
  --repo-owner=$REPO_OWNER \
  --repo-name=$REPO_NAME \
  --branch-pattern="^dev$" \
  --build-config=cloudbuild-staging.yaml \
  --name="safety-api-staging" \
  --description="Deploy safety-api to staging on dev branch push" \
  --project=$PROJECT_ID

if [ $? -eq 0 ]; then
    echo "✅ Staging trigger created"
else
    echo "❌ Failed to create staging trigger"
fi

# Step 5: List triggers to verify
echo ""
echo "📋 Verifying triggers..."
gcloud builds triggers list --project=$PROJECT_ID

echo ""
echo "🎉 GitHub to Cloud Build connection complete!"
echo ""
echo "📋 Your workflow:"
echo "1. Make changes in Cursor"
echo "2. Run: mario"
echo "3. Changes deploy automatically in 30-90 seconds"
echo ""
echo "🔗 Monitor deployments:"
echo "https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
