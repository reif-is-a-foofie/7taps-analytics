#!/bin/bash
# Instant deployment - deploy immediately, test in production

set -e

echo "⚡ Instant Deploy - Test in Production"
echo "======================================"

PROJECT_URL="https://taps-analytics-ui-zz2ztq5bjq-uc.a.run.app"

echo "🚀 Deploying immediately..."
gcloud builds submit --config cloudbuild.yaml . --quiet

echo "✅ Deployment complete!"
echo "🧪 Running production E2E tests..."

if python3 test_post_deploy_e2e.py; then
    echo "🎉 Production tests passed! Everything working."
else
    echo "❌ Production tests failed! Need to fix issues."
    echo ""
    echo "🔧 Quick fixes:"
    echo "   • Check logs: gcloud logs read --service=taps-analytics-ui --limit=50"
    echo "   • Test manually: $PROJECT_URL/ui/data-explorer"
    echo "   • Re-deploy if needed: ./instant_deploy.sh"
fi

echo ""
echo "🔗 Live URL: $PROJECT_URL/ui/data-explorer"
