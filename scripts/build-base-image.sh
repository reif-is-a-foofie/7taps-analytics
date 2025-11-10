#!/bin/bash
# Build and push the base image (run when requirements.txt changes)
# Usage: ./scripts/build-base-image.sh

set -e

PROJECT_ID="pol-a-477603"
SHORT_SHA=$(git rev-parse --short HEAD)

echo "Building base image with dependencies..."
echo "Project: $PROJECT_ID"
echo "SHA: $SHORT_SHA"

gcloud builds submit \
  --config=cloudbuild.base.yaml \
  --substitutions=SHORT_SHA=$SHORT_SHA \
  --project=$PROJECT_ID

echo "✓ Base image built and pushed successfully"
echo "Image: gcr.io/$PROJECT_ID/taps-analytics-ui-base:latest"

