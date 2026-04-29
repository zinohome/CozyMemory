#!/bin/bash
# 每次 docker compose up 都会执行的密码同步脚本
# 解决 init.sh 只在首次初始化运行的问题：
#   .env 中修改密码后，PG 数据卷中的旧密码不会自动更新，
#   导致 Cognee/Memobase/CozyMemory 连接认证失败。
#
# 运行方式：由 sync-passwords one-shot 容器调用，
#   依赖 postgres healthy 后执行 ALTER USER。
# 幂等：密码相同时 ALTER USER 无副作用。

set -e

COGNEE_DB_USER="${COGNEE_DB_USER:-cognee_user}"
COGNEE_DB_PASS="${COGNEE_DB_PASSWORD:?COGNEE_DB_PASSWORD required}"
MEMOBASE_DB_USER="${MEMOBASE_DB_USER:-memobase}"
MEMOBASE_DB_PASS="${MEMOBASE_DB_PASSWORD:?MEMOBASE_DB_PASSWORD required}"
COZYMEMORY_DB_USER="${COZYMEMORY_DB_USER:-cozymemory_user}"
COZYMEMORY_DB_PASS="${COZYMEMORY_DB_PASSWORD:?COZYMEMORY_DB_PASSWORD required}"

PG_HOST="${PG_HOST:-postgres}"
PG_PORT="${PG_PORT:-5432}"

echo "[sync-passwords] Syncing user passwords from environment variables ..."

PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$PG_HOST" -p "$PG_PORT" -U postgres -d postgres -v ON_ERROR_STOP=1 <<-EOSQL
    ALTER USER ${COGNEE_DB_USER} WITH PASSWORD '${COGNEE_DB_PASS}';
    ALTER USER ${MEMOBASE_DB_USER} WITH PASSWORD '${MEMOBASE_DB_PASS}';
    ALTER USER ${COZYMEMORY_DB_USER} WITH PASSWORD '${COZYMEMORY_DB_PASS}';
EOSQL

echo "[sync-passwords] All 3 user passwords synced successfully."
