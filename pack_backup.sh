#!/usr/bin/env bash
# Naudojimas: ./pack_backup.sh [OUT.zip]
set -euo pipefail
command -v zip >/dev/null || { echo "Reikia 'zip' (apt/brew install zip)."; exit 1; }

OUT="${1:-project-backup-$(date +%Y%m%d).zip}"
EX=(
  ".git/*" ".idea/*" ".vscode/*" "__pycache__/*" "*.pyc" ".mypy_cache/*" ".pytest_cache/*" ".ruff_cache/*" ".DS_Store"
  ".venv/*" "venv/*" "env/*" "node_modules/*" "dist/*" "build/*" "pip-wheel-metadata/*" "*.egg-info/*"
  "staticfiles/*" "logs/*" "*.log" "*.sqlite3" ".env" ".env.*"
)

zip -r "$OUT" . -x "${EX[@]}"
echo "Sukurta: $OUT"
