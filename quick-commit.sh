#!/bin/bash
# Quick commit and push script for frequent commits

set -e

echo "🚀 Quick Commit & Push"
echo "======================"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository!"
    exit 1
fi

# Get current branch
BRANCH=$(git branch --show-current)
echo "📋 Current branch: $BRANCH"

# Check for uncommitted changes
if git diff --quiet && git diff --cached --quiet; then
    echo "✅ No changes to commit"
    exit 0
fi

# Show status
echo ""
echo "📊 Git Status:"
git status --short

# Run pre-deployment tests
echo ""
echo "🧪 Running pre-deployment tests..."
if ! python3 test_pre_deployment.py; then
    echo "❌ Tests failed! Fix issues before committing."
    echo "💡 Run 'python3 test_pre_deployment.py' to see details"
    exit 1
fi

# Add all changes
echo ""
echo "📦 Staging all changes..."
git add .

# Generate commit message based on changes
CHANGED_FILES=$(git diff --cached --name-only)
FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l)

if [ "$FILE_COUNT" -eq 1 ]; then
    FILE_NAME=$(basename "$CHANGED_FILES")
    COMMIT_MSG="fix: update $FILE_NAME"
elif [ "$FILE_COUNT" -le 5 ]; then
    COMMIT_MSG="feat: update $FILE_COUNT files"
else
    COMMIT_MSG="feat: bulk update ($FILE_COUNT files)"
fi

# Add timestamp for uniqueness
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
COMMIT_MSG="$COMMIT_MSG - $TIMESTAMP"

echo ""
echo "💬 Commit message: $COMMIT_MSG"

# Commit
echo "📝 Committing..."
git commit -m "$COMMIT_MSG"

# Push
echo "🚀 Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

echo ""
echo "✅ Successfully committed and pushed!"
echo "🔗 Latest commit: $(git rev-parse --short HEAD)"
