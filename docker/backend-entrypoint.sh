#!/bin/sh
set -e

echo "Warte auf Datenbank und führe Migrationen aus..."
alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seede Initialdaten (Idempotent)..."
  python scripts/seed.py || echo "Seed übersprungen (vermutlich bereits vorhanden)."
fi

echo "Starte FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
