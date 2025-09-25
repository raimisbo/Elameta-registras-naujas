#!/bin/bash
# Sukuria švarų ZIP archyvą be nereikalingų failų

# Pavadinimas su data, pvz. Elameta_projektas_2025-09-22.zip
OUTFILE="Elameta_projektas_$(date +%Y-%m-%d).zip"

# Suspaudžiam viską, bet išmetam nereikalingus aplankus/failus
zip -r "$OUTFILE" . \
    -x "*.git*" \
       "*.idea*" \
       "*.vscode*" \
       "*.venv*" \
       "env/*" \
       "__pycache__/*" \
       "*.pyc" \
       "*.pyo" \
       "*.DS_Store" \
       "db.sqlite3*" \
       "*.log" \
       "*.coverage" \
       "*.cache/*" \
       "media/*"

echo "Sukurta: $OUTFILE"
