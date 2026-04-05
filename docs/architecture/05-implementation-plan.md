# 统一 AI 记忆服务平台 - 实施计划

**文档编号**: ARCH-IMPL-005  
**版本**: 2.0 (基于深入分析后修订)  
**状态**: 草案  
**创建日期**: 2026-04-05  
**作者**: 蟹小五 (AI 架构师)

---

## 1. 实施路线图

基于对 Mem0、Memobase、Cognee 的深入分析，我们采用**分阶段渐进式**实施策略。

### 1.1 总体时间线

```
Phase 0: 准备阶段 (Week 1-2)
    ├── 环境搭建
    ├── 技术验证
    └── 团队培训

Phase 1: MVP (Week 3-8)
    ├── 基础 API Gateway
    ├── Mem0 集成
    ├── 基础认证
    └── 简单路由

Phase 2: 增强 (Week 9-14)
    ├── Memobase 集成
    ├── Cognee 集成
    ├── 智能路由
    └── 结果融合

Phase 3: 优化 (Week 15-18)
    ├── 性能优化
    ├── 监控告警
    └── 文档完善

Phase 4: 生产 (Week 19-20)
    ├── 压力测试
    ├── 安全审计
    └── 上线部署
```

---

## 2. Phase 0: 准备阶段 (Week 1-2)

### 2.1 环境搭建

#### 2.1.1 开发环境
```bash
# 1. 克隆项目
git clone https://github.com/your-org/uamp.git
cd uamp

# 2. 安装依赖
uv sync  # 或 pip install -r requirements.txt

# 3. 启动开发服务
docker-compose up -d postgres redis minio

# 4. 初始化数据库
alembic upgrade head
```

#### 2.1.2 记忆引擎部署
```bash
# Mem0 (Docker)
cd deployment/mem0
docker-compose up -d

# Memobase (Docker)
cd deployment/memobase
docker-compose up -d

# Cognee (Docker)
cd deployment/cognee
docker-compose up -d

# Ollama (本地 LLM)
ollama pull qwen2.5:1.5b
ollama serve
```

#### 2.1.3 验证部署
```bash
# 验证 Mem0
curl http://localhost:8001/health

# 验证 Memobase
curl http://localhost:8019/api/v1/healthcheck

# 验证 Cognee
cognee-cli health

# 验证 Ollama
curl http://localhost:11434/api/tags
```

### 2.2 技术验证

#### 2.2.1 POC 目标
- [ ] 验证 Mem0 API 可用性
- [ ] 验证 Memobase API 可用性
- [ ] 验证 Cognee API 可用性
- [ ] 验证 FastAPI + Strawberry 集成
- [ ] 验证 grpc.aio 性能

#### 2.2.2 POC 代码示例
```python
# poc/test_mem0.py
from mem0 import Memory

memory = Memory.from_config({
    "vector_store": {
        "provider": "qdrant",
        "config": {"path": "/tmp/mem0"}
    },
    "llm": {
        "provider": "ollama",
        "config": {"model": "qwen2.5:1.5b"}
    }
})

result = memory.add(
    [{"role": "user", "content": "我喜欢 Python"}],
    user_id="test"
)
print(f"Mem0 POC: {result}")
```

### 2.3 团队培训

| 主题 | 内容 | 负责人 | 时长 |
|------|------|--------|------|
| FastAPI 进阶 | 异步编程、依赖注入 | 技术负责人 | 4h |
| GraphQL/Strawberry | Schema 设计、Resolver | 后端团队 | 4h |
| gRPC 基础 | Protobuf、流式处理 | 后端团队 | 4h |
| 记忆引擎 API | Mem0/Memobase/Cognee | 全员 | 8h |
| 系统架构 | 整体设计、数据流 | 架构师 | 4h |

---

## 3. Phase 1: MVP (Week 3-8)

### 3.1 目标

交付最小可行产品，包含：
- ✅ RESTful API (基础 CRUD)
- ✅ Mem0 集成
- ✅ JWT 认证
- ✅ 简单规则路由

### 3.2 Sprint 分解

#### Sprint 1 (Week 3-4): 基础框架
**目标**: 搭建 API Gateway 基础框架

**任务**:
- [ ] 创建 FastAPI 项目结构
- [ ] 配置数据库连接 (PostgreSQL)
- [ ] 实现用户认证 (FastAPI Users)
- [ ] 实现 API Key 管理
- [ ] 配置日志和监控

**交付物**:
```
apps/api-gateway/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   └── rest/
│   │       ├── users.py
│   │       └── auth.py
│   ├── models/
│   │   ├── user.py
│   │   └── api_key.py
│   └── schemas/
└── tests/
```

#### Sprint 2 (Week 5-6): Mem0 集成
**目标**: 集成 Mem0 记忆引擎

**任务**:
- [ ] 实现 Mem0 Adapter
- [ ] 实现记忆 CRUD API
- [ ] 实现简单路由 (规则-based)
- [ ] 编写单元测试
- [ ] 编写集成测试

**交付物**:
```python
# src/adapters/mem0_adapter.py
class Mem0Adapter:
    async def store(self, user_id, content, metadata):
        # 调用 Mem0 API
        pass
    
    async def retrieve(self, user_id, query, limit):
        # 调用 Mem0 search API
        pass

# src/api/rest/memories.py
@router.post("/memories")
async def create_memory(memory: MemoryCreate):
    adapter = Mem0Adapter()
    result = await adapter.store(...)
    return result
```

#### Sprint 3 (Week 7-8): 完善 MVP
**目标**: 完善 MVP 功能

**任务**:
- [ ] 实现记忆搜索 API
- [ ] 实现路由日志
- [ ] 实现缓存层 (Redis)
- [ ] API 文档 (OpenAPI)
- [ ] 性能基准测试

**交付物**:
- ✅ 可运行的 MVP 系统
- ✅ API 文档 (http://localhost:8000/docs)
- ✅ 性能测试报告

### 3.3 MVP 验收标准

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| API 响应时间 (P95) | < 200ms | wrk 压测 |
| 认证成功率 | > 99.9% | 日志分析 |
| Mem0 集成稳定性 | 无崩溃 | 72h 运行测试 |
| 代码覆盖率 | > 70% | pytest-cov |
| 文档完整性 | 100% API 有文档 | 人工检查 |

---

## 4. Phase 2: 增强 (Week 9-14)

### 4.1 目标

- ✅ 集成 Memobase
- ✅ 集成 Cognee
- ✅ 实现智能路由
- ✅ 实现结果融合

### 4.2 Sprint 分解

#### Sprint 4 (Week 9-10): Memobase 集成
**任务**:
- [ ] 实现 Memobase Adapter
- [ ] 实现用户画像 API
- [ ] 实现事件时间线 API
- [ ] 实现批量处理 (flush)

**代码结构**:
```python
# src/adapters/memobase_adapter.py
class MemobaseAdapter:
    def __init__(self, project_url, api_key):
        self.client = MemoBaseClient(project_url, api_key)
    
    async def store_profile(self, user_id, content):
        user = self.client.get_user(user_id)
        user.insert(ChatBlob(messages=content))
        user.flush(sync=True)
    
    async def get_profile(self, user_id):
        return self.client.get_user(user_id).profile(need_json=True)
```

#### Sprint 5 (Week 11-12): Cognee 集成
**任务**:
- [ ] 实现 Cognee Adapter
- [ ] 实现知识图谱 API
- [ ] 实现文档上传
- [ ] 实现图谱搜索

**代码结构**:
```python
# src/adapters/cognee_adapter.py
class CogneeAdapter:
    async def add_document(self, user_id, content):
        await cognee.add(content)
        await cognee.cognify()
    
    async def search_knowledge(self, user_id, query):
        results = await cognee.search(query)
        return self._transform(results)
```

#### Sprint 6 (Week 13-14): 智能路由 + 融合
**任务**:
- [ ] 实现 LLM 意图识别路由
- [ ] 实现混合路由 (规则 + LLM)
- [ ] 实现结果融合服务
- [ ] 实现去重和排序
- [ ] 实现缓存策略

**核心代码**:
```python
# src/services/fusion_service.py
class FusionService:
    async def merge_and_rank(self, memories, query, limit):
        # 1. 去重
        unique = self._deduplicate(memories)
        
        # 2. 评分
        scored = await self._score_memories(unique, query)
        
        # 3. 排序 (RRF)
        sorted_memories = self._reciprocal_rank_fusion(scored)
        
        # 4. 截断
        return sorted_memories[:limit]
```

### 4.3 增强版验收标准

| 指标 | 目标值 | 测量方法 |
|------|--------|---------|
| 支持引擎数 | 3 (Mem0/Memobase/Cognee) | 功能测试 |
| 路由准确率 | > 85% | 人工评估 |
| 融合结果质量 | > 单引擎 20% | A/B 测试 |
| 缓存命中率 | > 60% | 监控统计 |
| 系统可用性 | > 99.5% |  uptime 监控 |

---

## 5. Phase 3: 优化 (Week 15-18)

### 5.1 性能优化

#### 5.1.1 数据库优化
```sql
-- 添加索引
CREATE INDEX CONCURRENTLY idx_memories_user_type 
ON memories(user_id, memory_type);

-- 分析慢查询
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- 优化查询计划
EXPLAIN ANALYZE 
SELECT * FROM memories 
WHERE user_id = 'xxx' 
  AND memory_type = 'fact'
ORDER BY created_at DESC;
```

#### 5.1.2 缓存优化
```python
# 多级缓存策略
class CacheService:
    async def get(self, key):
        # L1: 内存缓存 (最快)
        if key in self.local_cache:
            return self.local_cache[key]
        
        # L2: Redis 缓存 (快)
        value = await self.redis.get(key)
        if value:
            self.local_cache[key] = value
            return value
        
        # L3: 数据库 (慢)
        return None
```

#### 5.1.3 并发优化
```python
# 异步并发调用多个引擎
async def parallel_query(user_id, query):
    tasks = [
        mem0_adapter.retrieve(user_id, query),
        memobase_adapter.retrieve(user_id, query),
        cognee_adapter.retrieve(user_id, query),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 5.2 监控告警

#### 5.2.1 Prometheus 指标
```python
# 自定义指标
REQUEST_COUNT = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

ROUTING_DECISIONS = Counter(
    'routing_decisions_total',
    'Total routing decisions',
    ['source', 'engines']
)

CACHE_HIT_RATE = Gauge(
    'cache_hit_rate',
    'Cache hit rate'
)
```

#### 5.2.2 Grafana 仪表板
- API 响应时间 (P50/P95/P99)
- 请求成功率
- 路由决策分布
- 缓存命中率
- 引擎调用延迟
- 数据库连接池

#### 5.2.3 告警规则
```yaml
# alerting.yml
groups:
  - name: uamp-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(api_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "错误率超过 5%"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, api_request_latency_seconds) > 0.5
        for: 10m
        annotations:
          summary: "P95 延迟超过 500ms"
      
      - alert: EngineUnavailable
        expr: up{job="mem0"} == 0
        for: 2m
        annotations:
          summary: "Mem0 引擎不可用"
```

### 5.3 文档完善

| 文档类型 | 内容 | 状态 |
|---------|------|------|
| API 文档 | OpenAPI/Swagger | ✅ 自动生成 |
| 用户指南 | 快速开始、使用示例 | 📝 编写中 |
| 开发文档 | 架构设计、代码规范 | 📝 编写中 |
| 运维文档 | 部署指南、故障排查 | 📝 编写中 |
| ADR | 架构决策记录 | ✅ 已完成 5 个 |

---

## 6. Phase 4: 生产 (Week 19-20)

### 6.1 压力测试

#### 6.1.1 测试场景
```yaml
场景 1: 高频写入
  - 并发用户：1000
  - 请求/秒：100
  - 持续时间：30 分钟
  - 目标：验证写入性能

场景 2: 高频读取
  - 并发用户：5000
  - 请求/秒：500
  - 持续时间：30 分钟
  - 目标：验证缓存效果

场景 3: 混合负载
  - 读写比例：30% 写 / 70% 读
  - 并发用户：2000
  - 持续时间：1 小时
  - 目标：验证综合性能
```

#### 6.1.2 压测工具
```bash
# wrk HTTP 压测
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/memories

# locust 负载测试
locust -f tests/load.py --users 1000 --spawn-rate 100
```

### 6.2 安全审计

#### 6.2.1 安全检查清单
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] CSRF 防护
- [ ] API Key 泄露防护
- [ ] 敏感数据加密
- [ ] 访问控制 (RBAC)
- [ ] 审计日志
- [ ] 依赖漏洞扫描

#### 6.2.2 安全工具
```bash
# 依赖漏洞扫描
safety check
pip-audit

# 代码安全扫描
bandit -r src/

# DAST 扫描
zap-baseline.py -t http://localhost:8000
```

### 6.3 上线部署

#### 6.3.1 部署流程
```bash
# 1. 构建 Docker 镜像
docker build -t uamp-api:latest .

# 2. 推送到镜像仓库
docker push registry.example.com/uamp-api:latest

# 3. 更新 Kubernetes 部署
kubectl set image deployment/uamp-api api=registry.example.com/uamp-api:latest

# 4. 滚动更新
kubectl rollout status deployment/uamp-api

# 5. 健康检查
kubectl exec -it uamp-api-xxx -- curl http://localhost:8000/health
```

#### 6.3.2 回滚计划
```bash
# 如果出现问题，快速回滚
kubectl rollout undo deployment/uamp-api

# 回滚到特定版本
kubectl rollout undo deployment/uamp-api --to-revision=2
```

---

## 7. 资源需求

### 7.1 人力资源

| 角色 | 人数 | 职责 |
|------|------|------|
| 架构师 | 1 | 系统设计、技术决策 |
| 后端开发 | 3 | API 开发、引擎集成 |
| 前端开发 | 1 | 管理界面 (可选) |
| DevOps | 1 | 部署、监控、CI/CD |
| QA | 1 | 测试、质量保证 |
| **总计** | **7** | |

### 7.2 基础设施

#### 开发环境
```yaml
服务器：4 核 8G × 3
存储：100GB SSD
网络：1Gbps
月成本：~$300
```

#### 生产环境 (初期)
```yaml
API Gateway: 2 核 4G × 3
PostgreSQL: 4 核 8G × 2 (主从)
Redis: 2 核 4G × 2 (集群)
MinIO: 2 核 4G × 2
记忆引擎：按需部署
月成本：~$1000
```

---

## 8. 风险管理

### 8.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM 延迟高 | 高 | 高 | 缓存 + 降级到规则路由 |
| 引擎 API 变更 | 中 | 中 | 适配器模式隔离 |
| 数据不一致 | 中 | 高 | 最终一致性 + 补偿机制 |
| 性能不达标 | 低 | 高 | 早期压测 + 持续优化 |

### 8.2 项目风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 人员流动 | 中 | 中 | 文档化 + 知识共享 |
| 需求变更 | 高 | 中 | 敏捷开发 + 迭代交付 |
| 依赖延期 | 低 | 中 | 提前识别 + 备选方案 |

---

## 9. 成功指标

### 9.1 技术指标

- [ ] API P95 延迟 < 200ms
- [ ] 系统可用性 > 99.5%
- [ ] 缓存命中率 > 60%
- [ ] 代码覆盖率 > 70%
- [ ] 零严重安全漏洞

### 9.2 业务指标

- [ ] 支持 3 个记忆引擎
- [ ] 路由准确率 > 85%
- [ ] 用户满意度 > 4.5/5
- [ ] 文档完整性 100%
- [ ] 团队培训完成率 100%

---

**END OF DOCUMENT**
