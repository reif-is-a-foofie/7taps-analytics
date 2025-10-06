#!/bin/bash

# Connect GitHub to Cloud Build via command line
echo "🔗 Connecting GitHub to Cloud Build..."

# Create production trigger
echo "🎯 Creating production trigger..."
gcloud builds triggers create github \
  --repo-owner=reif-is-a-foofie \
  --repo-name=7taps-analytics \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name="safety-api-production" \
  --description="Deploy safety-api to production on main branch push" \
  --substitutions="_GEMINI_API_KEY=your-actual-gemini-api-key"

# Create staging trigger  
echo "🎭 Creating staging trigger..."
gcloud builds triggers create github \
  --repo-owner=reif-is-a-foofie \
  --repo-name=7taps-analytics \
  --branch-pattern="^dev$" \
  --build-config=cloudbuild-staging.yaml \
  --name="safety-api-staging" \
  --description="Deploy safety-api to staging on dev branch push" \
  --substitutions="_GEMINI_API_KEY=your-actual-gemini-api-key"

echo "✅ GitHub triggers created!"
echo "🔗 Check triggers: gcloud builds triggers list"
