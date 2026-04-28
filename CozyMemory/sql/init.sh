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

# 全局设置 scram-sha-256 密码加密（修改 postgresql.conf，对所有会话生效）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "ALTER SYSTEM SET password_encryption = 'scram-sha-256';" \
  -c "SELECT pg_reload_conf();"

# 创建用户（带密码）、数据库和权限
# ALTER SYSTEM + pg_reload_conf 已确保 password_encryption=scram-sha-256
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${COGNEE_DB_USER} WITH PASSWORD '${COGNEE_DB_PASS}';
    CREATE DATABASE cognee_db OWNER ${COGNEE_DB_USER};
    ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cognee_db SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cognee_db TO ${COGNEE_DB_USER};

    CREATE USER ${MEMOBASE_DB_USER} WITH PASSWORD '${MEMOBASE_DB_PASS}';
    CREATE DATABASE memobase OWNER ${MEMOBASE_DB_USER};
    ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE memobase SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE memobase TO ${MEMOBASE_DB_USER};

    CREATE USER ${COZYMEMORY_DB_USER} WITH PASSWORD '${COZYMEMORY_DB_PASS}';
    CREATE DATABASE cozymemory OWNER ${COZYMEMORY_DB_USER};
    ALTER DATABASE cozymemory SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cozymemory SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cozymemory TO ${COZYMEMORY_DB_USER};
EOSQL

# Extensions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cognee_db" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "memobase" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cozymemory" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'

# 验证密码 hash 格式（应全部为 SCRAM-SHA-256）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c \
  "SELECT rolname, CASE WHEN rolpassword LIKE 'SCRAM-SHA-256%' THEN 'scram-sha-256' ELSE 'OTHER' END AS hash_type FROM pg_authid WHERE rolname IN ('${COGNEE_DB_USER}','${MEMOBASE_DB_USER}','${COZYMEMORY_DB_USER}');"

echo "[init.sh] All users, databases and extensions configured."

# 标记初始化完成
touch /var/lib/postgresql/data/pgdata/.init_done
