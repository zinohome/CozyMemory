#!/bin/bash
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

echo "[entrypoint] Seeding admin developer..."
python /app/scripts/seed_admin_developer.py
echo "[entrypoint] Seed complete."

exec "$@"
