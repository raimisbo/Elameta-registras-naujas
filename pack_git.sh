#!/usr/bin/env bash
# Naudojimas: ./pack_git.sh [REF] [OUT.zip]
set -euo pipefail
command -v git >/dev/null || { echo "Reikia 'git'."; exit 1; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "Neatrodo kaip Git repo."; exit 1; }

REF="${1:-HEAD}"
SAFE_REF="${REF//\//_}"
OUT="${2:-project-$(date +%Y%m%d)-${SAFE_REF}.zip}"

git archive --format=zip --output "$OUT" "$REF"
echo "Sukurta: $OUT"