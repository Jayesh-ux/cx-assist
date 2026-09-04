#!/bin/sh
set -e
echo "Applying migrations…"
alembic upgrade head

if [ "$1" = "worker" ]; then
  echo "Starting background worker…"
  exec python -m app.workers.run
fi

echo "Seeding demo data…"
python -m app.seed
echo "Starting API…"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000