-- 统一数据库初始化脚本
-- 当 pgvector 容器第一次启动时，将执行此脚本来创建多租户的逻辑库隔离

-- ===========================
-- Cognee 数据库与用户初始化
-- ===========================
CREATE USER cognee_user WITH PASSWORD 'cognee_password';
CREATE DATABASE cognee_db OWNER cognee_user;
ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
ALTER DATABASE cognee_db SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE cognee_db TO cognee_user;

-- 由于需要赋予 pgvector 能力，我们可以连接到并开启 vector
\c cognee_db
CREATE EXTENSION IF NOT EXISTS vector;

-- ===========================
-- Memobase 数据库与用户初始化
-- ===========================
CREATE USER memobase WITH PASSWORD 'memobase123';
CREATE DATABASE memobase OWNER memobase;
ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
ALTER DATABASE memobase SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE memobase TO memobase;

\c memobase
CREATE EXTENSION IF NOT EXISTS vector;
