#!/bin/bash
# Build a slim distribution tarball excluding large binaries and git history
# Usage: ./scripts/build_tarball.sh [output_name]

set -e

OUTPUT_NAME="${1:-7taps-analytics-release.tar.gz}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

echo "Building slim tarball: $OUTPUT_NAME"
echo "Excluding: .git/, Lessons Map/, archive/, and files from .gitignore"

# Use git archive if available (cleanest method)
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Using git archive (excludes .git/ automatically)..."
    git archive --format=tar.gz \
        --prefix=7taps-analytics/ \
        -o "$OUTPUT_NAME" \
        HEAD
    echo "✓ Created $OUTPUT_NAME using git archive"
else
    # Fallback: tar with explicit exclusions
    echo "Using tar with exclusions..."
    tar --exclude='.git' \
        --exclude='Lessons Map' \
        --exclude='archive' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.DS_Store' \
        --exclude='google-cloud-key.json' \
        --exclude='users_extracted.csv' \
        --exclude='.env' \
        --exclude='venv' \
        --exclude='env' \
        -czf "$OUTPUT_NAME" .
    echo "✓ Created $OUTPUT_NAME using tar"
fi

# Show size
SIZE=$(du -h "$OUTPUT_NAME" | cut -f1)
echo "Tarball size: $SIZE"
echo "Location: $REPO_ROOT/$OUTPUT_NAME"

