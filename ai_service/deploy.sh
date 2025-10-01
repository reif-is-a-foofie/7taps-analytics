#!/bin/bash
# Deploy AI Analysis Service to Cloud Functions

set -e

echo "🚀 Deploying AI Analysis Service to Cloud Functions"
echo "=================================================="

# Configuration
FUNCTION_NAME="ai-analysis-service"
REGION="us-central1"
RUNTIME="python311"
ENTRY_POINT="analyze_content"
MEMORY="512MB"
TIMEOUT="300s"

echo "📦 Function: $FUNCTION_NAME"
echo "🌍 Region: $REGION"
echo "⚡ Runtime: $RUNTIME"
echo ""

# Deploy the function
echo "🚀 Deploying..."
gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=. \
    --entry-point=analyze_content \
    --memory=$MEMORY \
    --timeout=$TIMEOUT \
    --trigger-http \
    --allow-unauthenticated \
    --quiet

echo ""
echo "✅ AI Analysis Service deployed!"
echo "🔗 URL: https://$REGION-taps-data.cloudfunctions.net/$FUNCTION_NAME"
echo ""
echo "📊 Test with:"
echo "curl -X POST https://$REGION-taps-data.cloudfunctions.net/$FUNCTION_NAME \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"content\": \"I feel sad today\", \"context\": \"general\"}'"
echo ""
echo "⏱️  Deploy time: ~30 seconds for algorithm changes!"
