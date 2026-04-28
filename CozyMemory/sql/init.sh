#!/bin/bash
# CozyMemory 统一数据库初始化脚本
# PostgreSQL + pgvector 首次启动时自动执行
# 密码从环境变量读取，不再硬编码

set -e

COGNEE_DB_USER="${COGNEE_DB_USER:-cognee_user}"
COGNEE_DB_PASS="${COGNEE_DB_PASSWORD:?COGNEE_DB_PASSWORD required}"
MEMOBASE_DB_USER="${MEMOBASE_DB_USER:-memobase}"
MEMOBASE_DB_PASS="${MEMOBASE_DB_PASSWORD:?MEMOBASE_DB_PASSWORD required}"
COZYMEMORY_DB_USER="${COZYMEMORY_DB_USER:-cozymemory_user}"
COZYMEMORY_DB_PASS="${COZYMEMORY_DB_PASSWORD:?COZYMEMORY_DB_PASSWORD required}"

# Step 1: 创建用户和数据库（trust 模式，不设密码）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${COGNEE_DB_USER};
    CREATE DATABASE cognee_db OWNER ${COGNEE_DB_USER};
    ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cognee_db SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cognee_db TO ${COGNEE_DB_USER};

    CREATE USER ${MEMOBASE_DB_USER};
    CREATE DATABASE memobase OWNER ${MEMOBASE_DB_USER};
    ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE memobase SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE memobase TO ${MEMOBASE_DB_USER};

    CREATE USER ${COZYMEMORY_DB_USER};
    CREATE DATABASE cozymemory OWNER ${COZYMEMORY_DB_USER};
    ALTER DATABASE cozymemory SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cozymemory SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cozymemory TO ${COZYMEMORY_DB_USER};
EOSQL

# Extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cognee_db" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "memobase" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cozymemory" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

# Step 2: 通过 TCP（127.0.0.1）设置密码 — 强制走 pg_hba.conf 的 scram-sha-256 认证路径
# 这确保密码 hash 使用 scram-sha-256 编码，与后续网络连接的认证方式一致
PGPASSWORD="${POSTGRES_PASSWORD}" psql -h 127.0.0.1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 <<-EOSQL2
    ALTER USER ${COGNEE_DB_USER} WITH PASSWORD '${COGNEE_DB_PASS}';
    ALTER USER ${MEMOBASE_DB_USER} WITH PASSWORD '${MEMOBASE_DB_PASS}';
    ALTER USER ${COZYMEMORY_DB_USER} WITH PASSWORD '${COZYMEMORY_DB_PASS}';
EOSQL2

echo "[init.sh] All users, databases, extensions, and passwords configured."

# Step 3: 验证每个用户可以通过 TCP 密码认证连接
for u_db in "${COGNEE_DB_USER}:${COGNEE_DB_PASS}:cognee_db" \
            "${MEMOBASE_DB_USER}:${MEMOBASE_DB_PASS}:memobase" \
            "${COZYMEMORY_DB_USER}:${COZYMEMORY_DB_PASS}:cozymemory"; do
    IFS=':' read -r user pass db <<< "$u_db"
    PGPASSWORD="$pass" psql -h 127.0.0.1 -U "$user" -d "$db" -c "SELECT 1" -q -t > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "[init.sh] ✓ $user@$db password OK"
    else
        echo "[init.sh] ✗ $user@$db password FAILED" >&2
        exit 1
    fi
done

# 标记初始化完成（healthcheck 检测此文件）
touch /var/lib/postgresql/data/pgdata/.init_done
