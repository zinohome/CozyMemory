#!/bin/bash
# 每次 docker compose up 都将 .env 密码同步到 PG
#
# 设计原则：
#   1. 首次部署：init.sh 已创建用户和密码，本脚本验证密码是否匹配
#   2. 后续部署：如果 .env 密码改了，ALTER USER 更新
#   3. 只在密码不匹配时才 ALTER USER，避免无谓的 SCRAM hash 重生成
#      （ALTER USER 即使密码相同也会生成新 salt/hash，产生短暂不一致窗口）

COGNEE_DB_USER="${COGNEE_DB_USER:-cognee_user}"
COGNEE_DB_PASS="${COGNEE_DB_PASSWORD:?COGNEE_DB_PASSWORD required}"
MEMOBASE_DB_USER="${MEMOBASE_DB_USER:-memobase}"
MEMOBASE_DB_PASS="${MEMOBASE_DB_PASSWORD:?MEMOBASE_DB_PASSWORD required}"
COZYMEMORY_DB_USER="${COZYMEMORY_DB_USER:-cozymemory_user}"
COZYMEMORY_DB_PASS="${COZYMEMORY_DB_PASSWORD:?COZYMEMORY_DB_PASSWORD required}"

PG_HOST="${PG_HOST:-cozy-pg}"
PG_PORT="${PG_PORT:-5432}"
MAX_RETRIES=40
DELAY=3

# 1. 等待 PG 超级用户可连接
echo "[sync-passwords] Waiting for PostgreSQL superuser connection ..."
for i in $(seq 1 "$MAX_RETRIES"); do
    if PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$PG_HOST" -p "$PG_PORT" -U postgres -d postgres -c "SELECT 1" >/dev/null 2>&1; then
        echo "[sync-passwords] PostgreSQL reachable (attempt $i)"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "[sync-passwords] FATAL: cannot connect to PostgreSQL after $MAX_RETRIES attempts" >&2
        exit 1
    fi
    sleep "$DELAY"
done

# 2. 等待 init.sh 完成（所有 3 个用户必须存在）
echo "[sync-passwords] Waiting for all 3 users to exist ..."
for i in $(seq 1 "$MAX_RETRIES"); do
    count=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$PG_HOST" -p "$PG_PORT" -U postgres -d postgres -tA \
        -c "SELECT count(*) FROM pg_roles WHERE rolname IN ('${COGNEE_DB_USER}','${MEMOBASE_DB_USER}','${COZYMEMORY_DB_USER}')" 2>/dev/null || echo "0")
    count=$(echo "$count" | tr -d '[:space:]')
    if [ "$count" = "3" ]; then
        echo "[sync-passwords] All 3 users found (attempt $i)"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "[sync-passwords] FATAL: only $count/3 users found after $MAX_RETRIES attempts" >&2
        exit 1
    fi
    echo "[sync-passwords] Found $count/3 users, retrying in ${DELAY}s ..."
    sleep "$DELAY"
done

# 3. 等 2 秒让 init.sh 的密码 hash 完全生效
sleep 2

# 4. 验证每个用户的密码，只在不匹配时 ALTER
changed=0
for pair in "${COGNEE_DB_USER}:${COGNEE_DB_PASS}" "${MEMOBASE_DB_USER}:${MEMOBASE_DB_PASS}" "${COZYMEMORY_DB_USER}:${COZYMEMORY_DB_PASS}"; do
    db_user="${pair%%:*}"
    db_pass="${pair#*:}"

    # 用用户自己的数据库验证（避免权限问题）；重试 3 次（init.sh 的 hash 可能还没完全生效）
    pw_ok=false
    for attempt in 1 2 3; do
        if PGPASSWORD="${db_pass}" psql -h "$PG_HOST" -p "$PG_PORT" -U "$db_user" -d postgres -c "SELECT 1" >/dev/null 2>&1; then
            pw_ok=true
            break
        fi
        sleep 1
    done

    if [ "$pw_ok" = true ]; then
        echo "[sync-passwords] ${db_user}: password OK"
    else
        echo "[sync-passwords] ${db_user}: password mismatch → ALTER USER"
        PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "$PG_HOST" -p "$PG_PORT" -U postgres -d postgres \
            -c "ALTER USER ${db_user} WITH PASSWORD '${db_pass}'" 2>&1
        changed=$((changed + 1))
    fi
done

if [ "$changed" -gt 0 ]; then
    echo "[sync-passwords] Updated $changed password(s), waiting 2s for PG to stabilize ..."
    sleep 2
else
    echo "[sync-passwords] All passwords match — no changes needed."
fi

echo "[sync-passwords] Done."
