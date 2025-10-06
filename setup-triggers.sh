#!/bin/bash

# Setup continuous deployment triggers for Cloud Build
echo "🚀 Setting up continuous deployment triggers..."

# Get current project
PROJECT_ID=$(gcloud config get-value project)
echo "📋 Project ID: $PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Create production trigger (main branch)
echo "🎯 Creating production trigger for main branch..."
gcloud builds triggers create github \
  --repo-owner=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\)\/\([^.]*\).*/\1/') \
  --repo-name=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\)\/\([^.]*\).*/\2/') \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name="safety-api-production" \
  --description="Deploy safety-api to production on main branch push"

# Create staging trigger (dev branch)
echo "🎭 Creating staging trigger for dev branch..."
gcloud builds triggers create github \
  --repo-owner=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\)\/\([^.]*\).*/\1/') \
  --repo-name=$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\)\/\([^.]*\).*/\2/') \
  --branch-pattern="^dev$" \
  --build-config=cloudbuild-staging.yaml \
  --name="safety-api-staging" \
  --description="Deploy safety-api to staging on dev branch push"

echo "✅ Triggers created successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Push to 'dev' branch → deploys to staging"
echo "2. Merge 'dev' to 'main' → deploys to production"
echo "3. Each push triggers automatic build and deployment"
echo ""
echo "🔗 Check triggers: gcloud builds triggers list"
