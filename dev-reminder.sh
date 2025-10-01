#!/bin/bash
# Development reminder script - run this periodically

echo "🔄 Development Reminder"
echo "======================="

# Check git status
if [ -d ".git" ]; then
    echo "📊 Git Status:"
    
    # Check for uncommitted changes
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "⚠️  You have uncommitted changes!"
        echo "   Run: ./quick-commit.sh or git qc"
        echo ""
        
        # Show what's changed
        echo "📝 Uncommitted files:"
        git status --short
        echo ""
    else
        echo "✅ Working directory is clean"
    fi
    
    # Check if we're behind origin
    git fetch origin > /dev/null 2>&1
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    
    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "⚠️  Your branch is behind origin!"
        echo "   Run: git pull"
        echo ""
    else
        echo "✅ Your branch is up to date with origin"
    fi
else
    echo "❌ Not in a git repository"
fi

echo ""
echo "💡 Best Practices:"
echo "   • Commit every logical change (even small ones)"
echo "   • Push at least once per hour"
echo "   • Use descriptive commit messages"
echo "   • Test before committing"
echo ""
echo "🚀 Quick Commands:"
echo "   • ./quick-commit.sh    - Quick commit & push"
echo "   • git qc               - Git alias for quick commit"
echo "   • git status           - Check current status"
