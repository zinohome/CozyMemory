-- CozyMemory PostgreSQL 初始化脚本
-- 创建 Memobase 所需的数据库结构

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_users_user_id ON users(user_id);

-- 记忆表 (Memobase 主表)
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL, -- 'profile', 'fact', 'event'
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI embedding 维度
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_type ON memories(memory_type);
CREATE INDEX idx_memories_created_at ON memories(created_at);
CREATE INDEX idx_memories_expires_at ON memories(expires_at);

-- 使用 pgvector 进行向量相似度搜索
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops);

-- 对话历史表
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    messages JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_session_id ON conversations(session_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

-- 记忆缓冲表 (用于批量处理)
CREATE TABLE IF NOT EXISTS memory_buffer (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_memory_buffer_status ON memory_buffer(status);
CREATE INDEX idx_memory_buffer_created_at ON memory_buffer(created_at);

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'create', 'read', 'update', 'delete'
    resource_type VARCHAR(50) NOT NULL, -- 'memory', 'user', 'conversation'
    resource_id UUID,
    old_value JSONB,
    new_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- 性能统计视图
CREATE OR REPLACE VIEW memory_stats AS
SELECT
    u.user_id,
    COUNT(m.id) AS total_memories,
    COUNT(CASE WHEN m.memory_type = 'profile' THEN 1 END) AS profile_count,
    COUNT(CASE WHEN m.memory_type = 'fact' THEN 1 END) AS fact_count,
    COUNT(CASE WHEN m.memory_type = 'event' THEN 1 END) AS event_count,
    MAX(m.created_at) AS last_memory_at
FROM users u
LEFT JOIN memories m ON u.id = m.user_id
GROUP BY u.user_id;

-- 自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 插入测试数据
INSERT INTO users (user_id, metadata) VALUES
    ('user_001', '{"name": "测试用户 1", "source": "wechat"}'),
    ('user_002', '{"name": "测试用户 2", "source": "feishu"}'),
    ('user_003', '{"name": "测试用户 3", "source": "web"}');

INSERT INTO memories (user_id, memory_type, content, metadata)
SELECT
    u.id,
    'profile',
    '我喜欢 Python 编程',
    '{"source": "chat", "confidence": 0.9}'
FROM users u WHERE u.user_id = 'user_001';

INSERT INTO memories (user_id, memory_type, content, metadata)
SELECT
    u.id,
    'fact',
    '我在北京工作',
    '{"source": "chat", "confidence": 0.85}'
FROM users u WHERE u.user_id = 'user_001';

-- 授予权限
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cozy;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cozy;

-- 输出初始化完成信息
SELECT 'CozyMemory 数据库初始化完成！' AS status;
SELECT COUNT(*) AS user_count FROM users;
SELECT COUNT(*) AS memory_count FROM memories;
