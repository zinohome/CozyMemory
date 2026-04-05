# 统一 AI 记忆服务平台 - 数据架构设计

**文档编号**: ARCH-DATA-002  
**版本**: 2.0 (基于深入分析后修订)  
**状态**: 草案  
**创建日期**: 2026-04-05  
**作者**: AI 架构师

---

## 1. 数据架构概览

### 1.1 统一记忆数据模型

基于对 Mem0、Memobase、Cognee 的深入分析，我们设计了统一的记忆数据模型：

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Memory Model                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Core Memory (统一核心记忆)                           │  │
│  │  - id: UUID                                          │  │
│  │  - user_id: String                                   │  │
│  │  - content: Text                                     │  │
│  │  - memory_type: Enum                                 │  │
│  │  - source: Enum (mem0/memobase/cognee)              │  │
│  │  - metadata: JSONB                                   │  │
│  │  - created_at: Timestamp                             │  │
│  │  - updated_at: Timestamp                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│         ┌────────────────┼────────────────┐                 │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ Fact Memory │ │Profile Memory│ │Knowledge    │           │
│  │ (Mem0)      │ │(Memobase)   │ │Memory       │           │
│  │             │ │             │ │(Cognee)     │           │
│  │ - fact:     │ │ - topic:    │ │ - document: │           │
│  │   String    │ │   String    │ │   String    │           │
│  │ - category: │ │ - sub_topic:│ │ - entities: │           │
│  │   String    │ │   String    │ │   JSON      │           │
│  │ -           │ │ - content:  │ │ - relations:│           │
│  │   confidence│ │   Text      │ │   JSON      │           │
│  │ - version:  │ │ -           │ │ - ontology: │           │
│  │   Integer   │ │   confidence│ │   String    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 记忆类型映射

| 统一类型 | Mem0 | Memobase | Cognee | 描述 |
|---------|------|----------|--------|------|
| **FACT** | ✅ 短期记忆 | ❌ | ❌ | LLM 提取的事实 |
| **PROFILE** | ❌ | ✅ 用户画像 | ❌ | 结构化用户信息 |
| **EVENT** | ❌ | ✅ 时间线事件 | ❌ | 带时间戳的事件 |
| **KNOWLEDGE** | ❌ | ❌ | ✅ 知识图谱 | 文档/实体/关系 |
| **PROCEDURAL** | ✅ 程序性记忆 | ❌ | ❌ | Agent 技能/规则 |

---

## 2. 数据库设计

### 2.1 PostgreSQL Schema

```sql
-- ========================================
-- 统一记忆服务平台数据库 Schema
-- ========================================

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API Keys 表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    name VARCHAR(255) NOT NULL,
    scopes VARCHAR(255) DEFAULT '*',
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 统一记忆表 (核心表)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    memory_type VARCHAR(50) NOT NULL,  -- fact|profile|event|knowledge|procedural
    source VARCHAR(50) NOT NULL,        -- mem0|memobase|cognee
    metadata JSONB DEFAULT '{}',
    similarity FLOAT,
    score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 索引
    INDEX idx_memories_user_id (user_id),
    INDEX idx_memories_type (memory_type),
    INDEX idx_memories_source (source),
    INDEX idx_memories_created_at (created_at)
);

-- Mem0 专用表 (事实记忆)
CREATE TABLE mem0_facts (
    id UUID PRIMARY KEY REFERENCES memories(id),
    fact TEXT NOT NULL,
    category VARCHAR(100),
    confidence FLOAT DEFAULT 0.9,
    version INTEGER DEFAULT 1,
    original_message_id UUID,
    
    -- 外键
    user_id UUID NOT NULL,
    agent_id UUID,
    run_id UUID,
    
    INDEX idx_mem0_facts_user (user_id),
    INDEX idx_mem0_facts_category (category)
);

-- Memobase 专用表 (画像记忆)
CREATE TABLE memobase_profiles (
    id UUID PRIMARY KEY REFERENCES memories(id),
    topic VARCHAR(100) NOT NULL,
    sub_topic VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.9,
    attributes JSONB DEFAULT '{}',
    
    user_id UUID NOT NULL,
    
    INDEX idx_memobase_profiles_user (user_id),
    INDEX idx_memobase_profiles_topic (topic, sub_topic)
);

-- Memobase 事件表 (时间线)
CREATE TABLE memobase_events (
    id UUID PRIMARY KEY REFERENCES memories(id),
    event_type VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE,
    summary TEXT,
    tags TEXT[],
    blob_id UUID,
    
    user_id UUID NOT NULL,
    
    INDEX idx_memobase_events_user (user_id),
    INDEX idx_memobase_events_time (timestamp),
    INDEX idx_memobase_events_tags USING GIN (tags)
);

-- Cognee 专用表 (知识图谱)
CREATE TABLE cognee_knowledge (
    id UUID PRIMARY KEY REFERENCES memories(id),
    document_id UUID,
    document_content TEXT,
    entities JSONB DEFAULT '[]',
    relations JSONB DEFAULT '[]',
    ontology VARCHAR(255),
    
    user_id UUID NOT NULL,
    
    INDEX idx_cognee_knowledge_user (user_id),
    INDEX idx_cognee_knowledge_entities USING GIN (entities)
);

-- 记忆历史表 (版本控制)
CREATE TABLE memory_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id UUID REFERENCES memories(id),
    operation VARCHAR(50) NOT NULL,  -- CREATE|UPDATE|DELETE
    old_content TEXT,
    new_content TEXT,
    old_metadata JSONB,
    new_metadata JSONB,
    changed_by UUID,  -- user_id 或 system
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_memory_history_memory (memory_id),
    INDEX idx_memory_history_changed_at (changed_at)
);

-- 会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_conversations_user (user_id)
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- user|assistant|system
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_messages_conversation (conversation_id),
    INDEX idx_messages_created_at (created_at)
);

-- 路由决策日志表 (用于分析和优化)
CREATE TABLE routing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    user_id UUID,
    selected_engines TEXT[],  -- [mem0, memobase, cognee]
    routing_source VARCHAR(50),  -- rules|llm
    confidence FLOAT,
    reasoning TEXT,
    execution_time_ms FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_routing_logs_user (user_id),
    INDEX idx_routing_logs_created_at (created_at)
);

-- 缓存表 (Redis 持久化备份)
CREATE TABLE cache (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    INDEX idx_cache_expires (expires_at)
);
```

### 2.2 向量存储设计

#### Mem0 - pgvector
```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- Mem0 向量表
CREATE TABLE mem0_embeddings (
    memory_id UUID PRIMARY KEY REFERENCES memories(id),
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- HNSW 索引 (高性能近似最近邻搜索)
    INDEX idx_mem0_embeddings_hnsw USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
);
```

#### Cognee - 图谱向量混合
```sql
-- Cognee 实体向量表
CREATE TABLE cognee_entity_embeddings (
    entity_id UUID PRIMARY KEY,
    entity_name TEXT NOT NULL,
    entity_type VARCHAR(100),
    embedding vector(1536),
    
    INDEX idx_cognee_entity_hnsw USING hnsw (embedding vector_cosine_ops)
);

-- Cognee 关系表 (图谱结构)
CREATE TABLE cognee_relations (
    id UUID PRIMARY KEY,
    source_entity_id UUID REFERENCES cognee_entity_embeddings(entity_id),
    target_entity_id UUID REFERENCES cognee_entity_embeddings(entity_id),
    relation_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    
    INDEX idx_cognee_relations_source (source_entity_id),
    INDEX idx_cognee_relations_target (target_entity_id),
    INDEX idx_cognee_relations_type (relation_type)
);
```

### 2.3 Redis 缓存设计

```yaml
# Redis 数据结构设计

# 1. 路由结果缓存 (TTL: 1 小时)
Key: routing:{query_hash}
Value: {
  "engines": ["mem0", "memobase"],
  "confidence": 0.92,
  "source": "llm",
  "reasoning": "..."
}

# 2. 用户上下文缓存 (TTL: 30 分钟)
Key: context:{user_id}:{context_hash}
Value: "格式化后的上下文字符串"

# 3. 记忆搜索结果缓存 (TTL: 5 分钟)
Key: search:{user_id}:{query_hash}
Value: [记忆列表 JSON]

# 4. 会话状态缓存 (TTL: 24 小时)
Key: session:{conversation_id}
Value: {
  "user_id": "...",
  "last_activity": "...",
  "message_count": 10
}

# 5. 限流计数器 (TTL: 1 分钟)
Key: ratelimit:{user_id}:{endpoint}
Value: 计数 (INCR)
```

---

## 3. 数据流设计

### 3.1 记忆写入流程

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Write Flow                         │
└─────────────────────────────────────────────────────────────┘

User Request (POST /memories)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  1. API Gateway - 认证和验证                                 │
│     - JWT/API Key 验证                                       │
│     - 请求体验证 (Pydantic)                                  │
│     - 限流检查 (Redis)                                       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Router Service - 路由决策                                │
│     - 规则匹配 (关键词/模式)                                 │
│     - LLM 意图识别 (可选)                                    │
│     - 输出：[mem0, memobase, cognee]                        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Adapter Layer - 引擎适配                                 │
│     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│     │ Mem0        │  │ Memobase    │  │ Cognee      │      │
│     │ Adapter     │  │ Adapter     │  │ Adapter     │      │
│     │             │  │             │  │             │      │
│     │ - Transform │  │ - Transform │  │ - Transform │      │
│     │ - HTTP Call │  │ - HTTP Call │  │ - HTTP Call │      │
│     └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Memory Engines - 并行执行                                │
│     - Mem0: LLM 提取事实 → 向量嵌入 → pgvector               │
│     - Memobase: 缓冲 → 批量处理 → PostgreSQL                │
│     - Cognee: 文档解析 → 图谱构建 → 图数据库                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Fusion Service - 结果融合                                │
│     - 收集各引擎返回结果                                     │
│     - 去重 (ID/内容哈希)                                     │
│     - 评分排序 (相关性 + 时间 + 来源权重)                    │
│     - 截断到 limit                                           │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Response - 返回统一格式                                  │
│     {                                                        │
│       "memories": [...],                                     │
│       "routing": {...},                                      │
│       "execution_time_ms": 150                               │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 记忆读取流程

```
User Request (GET /memories/search?query=xxx)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Cache Lookup (Redis)                                    │
│     - 检查缓存命中                                           │
│     - Hit: 直接返回 (P50 < 5ms)                             │
│     - Miss: 继续向下                                         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Router Service - 路由决策                                │
│     - 分析查询意图                                           │
│     - 选择引擎：                                              │
│       * 事实查询 → Mem0                                     │
│       * 画像查询 → Memobase                                 │
│       * 知识查询 → Cognee                                   │
│       * 模糊查询 → 全部引擎                                 │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Parallel Engine Query                                   │
│     - Mem0: 向量相似度搜索 (pgvector)                        │
│     - Memobase: SQL 查询 + 标签过滤                          │
│     - Cognee: 图谱遍历 + 向量搜索                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Fusion Service - 结果融合                                │
│     - 合并所有结果                                           │
│     - 去重                                                   │
│     - 重新排序 (RRF: Reciprocal Rank Fusion)                │
│     - 截断                                                   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Cache Store (Redis)                                     │
│     - 存储结果 (TTL: 5 分钟)                                  │
│     - 异步写入，不阻塞响应                                   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Response                                                 │
│     {                                                        │
│       "memories": [...],                                     │
│       "cache_hit": false,                                    │
│       "execution_time_ms": 120                               │
│     }                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 数据治理

### 4.1 数据质量

| 维度 | 策略 | 实施 |
|------|------|------|
| **准确性** | LLM 置信度阈值 | 置信度<0.6 的记忆标记为低质量 |
| **完整性** | 必填字段验证 | Pydantic Schema 验证 |
| **一致性** | 统一数据模型 | 适配器模式转换 |
| **时效性** | TTL 自动过期 | Redis/数据库定期清理 |
| **可追溯性** | 版本历史 | memory_history 表 |

### 4.2 数据安全

```sql
-- 敏感数据加密
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- API Key 加密存储
INSERT INTO api_keys (key_hash, ...)
VALUES (pgp_sym_encrypt('sk_xxx', 'encryption_key'), ...);

-- 用户数据行级安全 (RLS)
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_policy ON memories
    USING (user_id = current_setting('app.current_user_id')::UUID);
```

### 4.3 数据保留策略

| 数据类型 | 保留期限 | 清理策略 |
|---------|---------|---------|
| 活跃记忆 | 永久 | 无 |
| 记忆历史 | 90 天 | 定期归档 |
| 路由日志 | 30 天 | 自动删除 |
| 缓存数据 | 1 小时 | TTL 自动过期 |
| 会话数据 | 24 小时 | TTL 自动过期 |

---

## 5. 性能优化

### 5.1 索引策略

```sql
-- 复合索引 (高频查询模式)
CREATE INDEX idx_memories_user_type_created 
ON memories(user_id, memory_type, created_at DESC);

-- 覆盖索引 (避免回表)
CREATE INDEX idx_memories_covering
ON memories(user_id, created_at)
INCLUDE (content, memory_type, source);

-- 部分索引 (只索引活跃数据)
CREATE INDEX idx_memories_active
ON memories(user_id, created_at)
WHERE metadata->>'is_deleted' IS NULL;
```

### 5.2 分区策略

```sql
-- 按月分区 (大规模数据)
CREATE TABLE memories_partitioned (
    LIKE memories INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE memories_2026_04 PARTITION OF memories_partitioned
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### 5.3 读写分离

```yaml
# 数据库连接配置
database:
  primary:
    host: postgres-primary
    port: 5432
    role: write
    
  replicas:
    - host: postgres-replica-1
      port: 5432
      role: read
    - host: postgres-replica-2
      port: 5432
      role: read

# 路由规则
# - 写操作 → Primary
# - 读操作 → Replica (负载均衡)
```

---

**END OF DOCUMENT**
