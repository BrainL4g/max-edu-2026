#!/bin/sh
set -eu

echo "[entrypoint] Applying database migrations..."
if alembic -c backend/alembic.ini upgrade head; then
    echo "[entrypoint] Migrations applied."
else
    echo "[entrypoint] WARN: alembic upgrade failed (legacy schema?), " \
        "continuing with app-level create_all + seed." >&2
fi

echo "[entrypoint] Starting API server on :8000..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000