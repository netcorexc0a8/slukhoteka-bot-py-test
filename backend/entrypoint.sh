#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
python -m migrations.migrate

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
