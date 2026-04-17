-- CozyMemory 统一数据库初始化脚本
-- PostgreSQL + pgvector 首次启动时自动执行

-- ===========================
-- Cognee 数据库初始化
-- ===========================
CREATE USER cognee_user WITH PASSWORD 'cognee_password';
CREATE DATABASE cognee_db OWNER cognee_user;
ALTER DATABASE cognee_db SET default_transaction_isolation TO 'read committed';
ALTER DATABASE cognee_db SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE cognee_db TO cognee_user;

\c cognee_db
CREATE EXTENSION IF NOT EXISTS vector;

-- ===========================
-- Memobase 数据库初始化
-- ===========================
CREATE USER memobase WITH PASSWORD 'memobase123';
CREATE DATABASE memobase OWNER memobase;
ALTER DATABASE memobase SET default_transaction_isolation TO 'read committed';
ALTER DATABASE memobase SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE memobase TO memobase;

\c memobase
CREATE EXTENSION IF NOT EXISTS vector;
