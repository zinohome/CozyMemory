#!/bin/sh
# Replace build-time placeholder with runtime NEXT_PUBLIC_API_URL
# This mirrors the same pattern used by mem0-webui.

set -e

PLACEHOLDER="__COZY_API_URL__"
RUNTIME_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

if [ "$RUNTIME_URL" != "$PLACEHOLDER" ]; then
  echo "[entrypoint] Injecting NEXT_PUBLIC_API_URL=${RUNTIME_URL}"
  find /app/.next/static -type f -name "*.js" | xargs -r sed -i "s|${PLACEHOLDER}|${RUNTIME_URL}|g"
else
  echo "[entrypoint] NEXT_PUBLIC_API_URL not set, using placeholder (development mode)"
fi

exec "$@"
