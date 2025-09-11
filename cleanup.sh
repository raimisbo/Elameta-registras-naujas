#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./cleanup.sh            # cleans current directory (repo root)
#   ./cleanup.sh /path/to/project  # cleans the given path
TARGET_DIR="${1:-.}"
cd "$TARGET_DIR"

echo "Cleaning Python caches..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) -delete

echo "Cleaning macOS cruft..."
find . -type f -name ".DS_Store" -delete
find . -type f -name "._*" -delete

echo "Cleaning IDE files..."
rm -rf .idea *.iml .vscode 2>/dev/null || true

echo "Done."
