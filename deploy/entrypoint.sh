#!/bin/bash
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head
echo "[entrypoint] Migrations complete."

echo "[entrypoint] Seeding admin developer..."
python -m scripts.seed_admin_developer
echo "[entrypoint] Seed complete."

exec "$@"
