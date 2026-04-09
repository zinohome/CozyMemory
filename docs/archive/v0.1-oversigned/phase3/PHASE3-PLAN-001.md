# Phase 3 开发计划

**阶段**: Phase 3 - 多引擎支持 + 生产部署  
**开始日期**: 2026-04-07  
**预计完成**: 2026-04-14 (1 周)  
**负责人**: 蟹小五🦀  

---

## 🎯 目标

将 CozyMemory 从原型系统升级为**生产级**记忆管理平台。

**核心目标**:
1. 实现真实存储引擎 (SQLite + Vector)
2. 完成 Docker 容器化部署
3. 添加 Redis 缓存支持
4. 实现动态权重路由
5. 完善监控和日志

---

## 📅 日程安排

### Day 1: SQLite 引擎 (今天)

**目标**: 实现本地持久化存储引擎

**任务**:
- [ ] 设计 SQLite 数据模型
- [ ] 实现 SQLiteAdapter
- [ ] 编写单元测试
- [ ] 集成到 EnhancedMemoryService
- [ ] 性能测试

**交付物**:
- `src/adapters/sqlite_adapter.py`
- `src/tests/unit/test_sqlite_adapter.py`
- 迁移脚本 (可选)

**预计时间**: 4-6 小时

---

### Day 2: 向量数据库引擎

**目标**: 实现语义搜索能力

**任务**:
- [ ] 选择向量数据库 (Chroma vs FAISS)
- [ ] 实现 VectorAdapter
- [ ] 文本嵌入 (Embedding) 集成
- [ ] 相似度搜索
- [ ] 单元测试

**交付物**:
- `src/adapters/vector_adapter.py`
- `src/embeddings/base.py`
- `src/tests/unit/test_vector_adapter.py`

**预计时间**: 6-8 小时

---

### Day 3: Docker 容器化

**目标**: 实现一键部署

**任务**:
- [ ] 编写 Dockerfile
- [ ] 创建 docker-compose.yml
- [ ] 配置生产环境变量
- [ ] 添加健康检查
- [ ] 测试容器化部署

**交付物**:
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `docs/deployment/DOCKER-DEPLOYMENT.md`

**预计时间**: 3-4 小时

---

### Day 4: Redis 缓存 + 监控

**目标**: 完善缓存和监控

**任务**:
- [ ] Redis 配置优化
- [ ] 添加 Prometheus 指标
- [ ] 创建 Grafana 仪表板
- [ ] 实现性能告警
- [ ] 日志聚合

**交付物**:
- `monitoring/prometheus.yml`
- `monitoring/grafana-dashboard.json`
- `src/metrics/prometheus_metrics.py`

**预计时间**: 4-5 小时

---

### Day 5: 动态权重路由

**目标**: 智能路由优化

**任务**:
- [ ] 实现性能监控
- [ ] 动态权重算法
- [ ] 自动降级机制
- [ ] 熔断器实现
- [ ] 测试验证

**交付物**:
- `src/routers/dynamic_weight_router.py`
- `src/utils/circuit_breaker.py`

**预计时间**: 4-5 小时

---

### Day 6-7: 集成测试 + 文档

**目标**: 全面测试和文档

**任务**:
- [ ] 端到端集成测试
- [ ] 压力测试
- [ ] 更新 README
- [ ] 编写部署指南
- [ ] Phase 3 总结报告

**交付物**:
- `src/tests/integration/`
- `docs/deployment/PRODUCTION-GUIDE.md`
- `docs/phase3/PHASE3-SUMMARY-001.md`

**预计时间**: 6-8 小时

---

## 📊 技术规格

### 1. SQLite 引擎

**数据模型**:
```sql
CREATE TABLE memories (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    memory_type VARCHAR(32) NOT NULL,
    source VARCHAR(32),
    metadata JSON,
    confidence FLOAT DEFAULT 0.9,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_memory_type (memory_type),
    INDEX idx_created_at (created_at)
);
```

**特性**:
- 支持 CRUD 操作
- 全文搜索 (FTS5)
- 批量操作
- 事务支持

---

### 2. 向量数据库引擎

**选型**: ChromaDB (轻量，易集成)

**特性**:
- 文本嵌入 (sentence-transformers)
- 余弦相似度搜索
- 元数据过滤
- 持久化存储

**配置**:
```python
CHROMA_PERSIST_DIR = "./chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.7
```

---

### 3. Docker 部署

**架构**:
```
┌─────────────────┐
│   Nginx (反向代理)  │
└────────┬────────┘
         │
┌────────▼────────┐
│  CozyMemory API │
│  (FastAPI)      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼─────┐
│Redis │  │ChromaDB│
└──────┘  └────────┘
```

**资源需求**:
- CPU: 2 核心
- RAM: 2GB
- 存储：10GB

---

### 4. 监控指标

**Prometheus 指标**:
- `cozymemory_requests_total` - 总请求数
- `cozymemory_request_duration_seconds` - 请求延迟
- `cozymemory_cache_hits_total` - 缓存命中数
- `cozymemory_engine_queries_total` - 引擎查询数
- `cozymemory_errors_total` - 错误数

**Grafana 仪表板**:
- 请求量趋势
- 延迟分布
- 缓存命中率
- 引擎性能对比
- 错误率

---

## ✅ 验收标准

### 功能验收

- [ ] SQLite 引擎通过所有测试
- [ ] 向量引擎支持语义搜索
- [ ] Docker 一键部署成功
- [ ] Redis 缓存正常工作
- [ ] 动态路由自动优化

### 性能验收

- [ ] SQLite 查询 <10ms
- [ ] 向量搜索 <50ms
- [ ] 缓存命中率 >90%
- [ ] 并发支持 >50 QPS
- [ ] P95 延迟 <100ms

### 质量验收

- [ ] 测试覆盖率 >85%
- [ ] 无严重 Bug
- [ ] 文档完整
- [ ] 部署指南清晰
- [ ] 监控告警完善

---

## 📚 参考文档

- [Phase 1 总结](../phase1/TEST-REPORT-001.md)
- [Phase 2 总结](../phase2/PHASE2-SUMMARY-001.md)
- [Phase 2 性能报告](../phase2/PERF-BENCHMARK-001.md)
- [架构设计](../ARCHITECTURE.md)

---

## 🎯 成功指标

**技术指标**:
- 测试通过率：100%
- 代码覆盖率：>85%
- 性能达标率：100%

**业务指标**:
- 部署时间：<5 分钟
- 运维复杂度：低
- 用户满意度：高

---

**计划制定时间**: 2026-04-07  
**制定者**: 蟹小五🦀  
**状态**: 🚀 进行中

🦀 **Phase 3 - Production Ready!** 🚀
