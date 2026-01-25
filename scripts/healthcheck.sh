#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "== Project root: $PROJECT_ROOT"

# 1) Virtualenv aktyvavimas (jei yra)
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
  echo "== venv: .venv activated"
else
  echo "== WARNING: .venv not found, continuing with system python"
fi

echo "== Python:"
python -V

echo "== Django system check:"
python manage.py check

echo "== Migration check (no apply):"
python manage.py makemigrations --check --dry-run

echo "== Migrate (apply if needed):"
python manage.py migrate

echo "== Smoke test (Django test client):"
python scripts/smoke_test.py

echo "== OK: healthcheck finished"
