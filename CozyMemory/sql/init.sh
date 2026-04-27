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

# 强制使用 scram-sha-256 密码加密（pg_hba.conf 对网络连接要求 scram-sha-256）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SET password_encryption = 'scram-sha-256';"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Cognee
    CREATE USER ${COGNEE_DB_USER} WITH PASSWORD '${COGNEE_DB_PASS}';
    CREATE DATABASE cognee_db OWNER ${COGNEE_DB_USER};
    ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cognee_db SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cognee_db TO ${COGNEE_DB_USER};

    -- Memobase
    CREATE USER ${MEMOBASE_DB_USER} WITH PASSWORD '${MEMOBASE_DB_PASS}';
    CREATE DATABASE memobase OWNER ${MEMOBASE_DB_USER};
    ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE memobase SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE memobase TO ${MEMOBASE_DB_USER};

    -- CozyMemory
    CREATE USER ${COZYMEMORY_DB_USER} WITH PASSWORD '${COZYMEMORY_DB_PASS}';
    CREATE DATABASE cozymemory OWNER ${COZYMEMORY_DB_USER};
    ALTER DATABASE cozymemory SET default_transaction_isolation TO 'read committed';
    ALTER DATABASE cozymemory SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE cozymemory TO ${COZYMEMORY_DB_USER};
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cognee_db" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "memobase" -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "cozymemory" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
