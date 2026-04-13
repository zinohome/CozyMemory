# Phase 2 实施计划

**文档编号**: PHASE2-PLAN-001  
**版本**: 1.0  
**日期**: 2026-04-06  
**阶段**: Phase 2 (缓存层 + 智能路由)  
**作者**: AI 架构师  
**审批**: 张老师  

---

## 📋 文档控制

| 版本 | 日期 | 作者 | 变更说明 | 审批 |
|------|------|------|----------|------|
| 1.0 | 2026-04-06 | AI 架构师 | 初稿 | 张老师 |

---

## 📊 概览

**阶段目标**: 实现缓存层和智能路由，提升系统性能和可扩展性

**预计时间**: 1-2 天 (2026-04-06 ~ 2026-04-08)

**关键交付物**:
- ✅ 缓存层实现 (Redis + Memory)
- ✅ 智能路由实现 (意图 + 轮询 + 权重)
- ✅ 结果融合实现 (RRF + 权重)
- ✅ 单元测试 (90%+ 覆盖率)
- ✅ 集成测试
- ✅ 性能基准测试
- ✅ 完整文档

---

## 📅 详细计划

### Day 1: 缓存层实现 (2026-04-06)

#### 上午 (09:00-12:00) - 缓存层核心实现

**任务清单**:
- [ ] 创建 `src/cache/` 目录结构
- [ ] 实现 `src/cache/base.py` (BaseCache 抽象基类)
- [ ] 实现 `src/cache/memory_cache.py` (LRU 内存缓存)
- [ ] 实现 `src/cache/redis_cache.py` (Redis 缓存)
- [ ] 实现缓存保护机制 (穿透/雪崩)

**验收标准**:
- [ ] 代码通过 Black 格式化
- [ ] 类型注解完整
- [ ] 文档字符串完整
- [ ] 可导入无错误

**预计代码量**: ~400 行

---

#### 下午 (13:00-18:00) - 缓存层测试

**任务清单**:
- [ ] 创建 `tests/unit/test_cache_base.py` (8 个测试)
- [ ] 创建 `tests/unit/test_memory_cache.py` (15 个测试)
- [ ] 创建 `tests/unit/test_redis_cache.py` (15 个测试，使用 Mock)
- [ ] 创建 `tests/unit/test_cache_protection.py` (10 个测试)
- [ ] 运行测试，检查覆盖率
- [ ] 修复未覆盖代码

**验收标准**:
- [ ] 测试通过率 100%
- [ ] 缓存层覆盖率 ≥90%
- [ ] 测试执行时间 <30 秒

**预计测试代码量**: ~350 行

---

#### 晚上 (可选) - 缓存服务集成

**任务清单**:
- [ ] 实现 `src/services/cache_service.py`
- [ ] 修改 `MemoryService` 集成缓存
- [ ] 编写集成测试

**备注**: 如时间不足，移至 Day 2 上午

---

### Day 2: 路由层 + 融合层 (2026-04-07)

#### 上午 (09:00-12:00) - 路由层实现

**任务清单**:
- [ ] 创建 `src/routers/` 目录结构
- [ ] 实现 `src/routers/base.py` (BaseRouter 抽象基类)
- [ ] 实现 `src/routers/intent_router.py` (意图识别路由)
- [ ] 实现 `src/routers/round_robin_router.py` (轮询路由)
- [ ] 实现 `src/routers/weighted_router.py` (权重路由)
- [ ] 实现 `src/services/router_service.py` (路由服务)

**验收标准**:
- [ ] 代码通过 Black 格式化
- [ ] 类型注解完整
- [ ] 文档字符串完整
- [ ] 可导入无错误

**预计代码量**: ~350 行

---

#### 下午 (13:00-16:00) - 路由层测试

**任务清单**:
- [ ] 创建 `tests/unit/test_router_base.py` (6 个测试)
- [ ] 创建 `tests/unit/test_intent_router.py` (12 个测试)
- [ ] 创建 `tests/unit/test_round_robin_router.py` (8 个测试)
- [ ] 创建 `tests/unit/test_weighted_router.py` (10 个测试)
- [ ] 创建 `tests/unit/test_router_service.py` (10 个测试)
- [ ] 运行测试，检查覆盖率

**验收标准**:
- [ ] 测试通过率 100%
- [ ] 路由层覆盖率 ≥90%

**预计测试代码量**: ~250 行

---

#### 下午 (16:00-18:00) - 融合层实现

**任务清单**:
- [ ] 创建 `src/fusion/` 目录结构
- [ ] 实现 `src/fusion/rrf.py` (RRF 算法)
- [ ] 实现 `src/fusion/weighted.py` (权重融合)
- [ ] 实现去重函数
- [ ] 编写测试 (24 个测试)

**验收标准**:
- [ ] 代码通过 Black 格式化
- [ ] 类型注解完整
- [ ] 融合层覆盖率 ≥90%

**预计代码量**: ~150 行 (含测试)

---

### Day 3: 集成测试 + 性能测试 (2026-04-08)

#### 上午 (09:00-12:00) - 集成测试

**任务清单**:
- [ ] 创建 `tests/integration/test_cache_integration.py` (8 个测试)
- [ ] 创建 `tests/integration/test_router_integration.py` (8 个测试)
- [ ] 创建 `tests/integration/test_fusion_integration.py` (6 个测试)
- [ ] 端到端流程测试
- [ ] 多引擎并发测试

**验收标准**:
- [ ] 集成测试通过率 100%
- [ ] 端到端流程验证通过

**预计测试代码量**: ~200 行

---

#### 下午 (13:00-16:00) - 性能测试

**任务清单**:
- [ ] 安装 pytest-benchmark
- [ ] 创建 `tests/performance/test_cache_benchmark.py` (5 个测试)
- [ ] 创建 `tests/performance/test_router_benchmark.py` (5 个测试)
- [ ] 运行性能基准测试
- [ ] 记录性能指标
- [ ] 对比 Phase 1 基准

**验收标准**:
- [ ] 缓存命中延迟 <20ms
- [ ] 路由决策延迟 <5ms
- [ ] 吞吐量提升 >3x

**预计测试代码量**: ~150 行

---

#### 下午 (16:00-18:00) - 文档 + 代码审查

**任务清单**:
- [ ] 更新 README.md (Phase 2 功能说明)
- [ ] 编写 Phase 2 测试报告
- [ ] 编写 Phase 2 总结文档
- [ ] 代码审查 (自查)
- [ ] 更新 PROGRESS.md
- [ ] 提交代码到 GitHub

**验收标准**:
- [ ] 文档完整
- [ ] 代码审查通过
- [ ] 代码已推送

---

## 📦 交付物清单

### 代码文件

#### 新增文件
```
src/cache/
├── __init__.py
├── base.py              # 缓存基类
├── memory_cache.py      # LRU 内存缓存
└── redis_cache.py       # Redis 缓存

src/routers/
├── __init__.py
├── base.py              # 路由基类
├── intent_router.py     # 意图识别路由
├── round_robin_router.py # 轮询路由
├── weighted_router.py   # 权重路由
└── router_service.py    # 路由服务

src/fusion/
├── __init__.py
├── rrf.py               # RRF 算法
└── weighted.py          # 权重融合

src/services/
├── cache_service.py     # 缓存服务 (新增)
└── router_service.py    # 路由服务 (新增，或合并到 routers/)

src/models/
├── cache.py             # 缓存模型 (新增)
└── router.py            # 路由模型 (新增)
```

#### 修改文件
```
src/services/memory_service.py  # 集成缓存和路由
src/api/v1/routes.py            # 新增缓存和路由端点
src/utils/config.py             # 新增缓存和路由配置
```

---

### 测试文件

```
tests/unit/
├── test_cache_base.py
├── test_memory_cache.py
├── test_redis_cache.py
├── test_cache_protection.py
├── test_router_base.py
├── test_intent_router.py
├── test_round_robin_router.py
├── test_weighted_router.py
├── test_router_service.py
├── test_rrf_fusion.py
├── test_weighted_fusion.py
└── test_deduplication.py

tests/integration/
├── test_cache_integration.py
├── test_router_integration.py
└── test_fusion_integration.py

tests/performance/
├── test_cache_benchmark.py
└── test_router_benchmark.py
```

---

### 文档文件

```
docs/phase2/
├── PHASE2-DESIGN-001.md      # 详细设计文档 ✅ 已完成
├── PHASE2-PLAN-001.md        # 实施计划 ✅ 本文件
├── PHASE2-TEST-REPORT-001.md # 测试报告 (待完成)
└── PHASE2-SUMMARY-001.md     # 阶段总结 (待完成)
```

---

## 📊 验收标准

### 功能验收

- [ ] 缓存层正常工作 (Redis + Memory)
- [ ] 缓存穿透/雪崩保护有效
- [ ] 三种路由策略可切换
- [ ] RRF 融合算法正确
- [ ] 权重融合算法正确
- [ ] 去重功能正常

### 测试验收

- [ ] 单元测试总数 ≥150 个
- [ ] 测试通过率 100%
- [ ] 总体覆盖率 ≥90%
- [ ] 集成测试通过
- [ ] 性能测试达标

### 性能验收

| 指标 | Phase 1 | Phase 2 目标 | 验收 |
|------|---------|-------------|------|
| 查询延迟 (缓存命中) | ~50ms | <20ms | ☐ |
| 查询延迟 (缓存未命中) | ~50ms | <100ms | ☐ |
| 吞吐量 | 100 req/s | 500 req/s | ☐ |
| 缓存命中率 | N/A | >80% | ☐ |

### 文档验收

- [ ] README.md 更新
- [ ] 设计文档完整
- [ ] 测试报告完整
- [ ] 阶段总结完成
- [ ] API 文档更新

---

## 🔧 技术准备

### 依赖安装

```bash
# 安装新依赖
pip install redis>=5.0.0
pip install pytest-benchmark>=4.0.0

# 开发环境
pip install -r requirements-dev.txt
```

### 环境配置

```bash
# .env 文件添加
REDIS_URL=redis://localhost:6379/0
REDIS_PREFIX=cozymemory:
CACHE_TTL=300

# 路由配置
ROUTER_STRATEGY=intent
FUSION_STRATEGY=rrf
```

### 本地 Redis (可选)

```bash
# macOS
brew install redis
brew services start redis

# 或使用 Docker
docker run -d -p 6379:6379 --name cozymemory-redis redis:latest
```

---

## ⚠️ 风险与应对

### 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| Redis 连接问题 | 低 | 高 | 降级到内存缓存、Mock 测试 |
| 缓存一致性问题 | 中 | 中 | 明确失效策略、版本号机制 |
| 路由策略效果不佳 | 中 | 中 | 可配置切换、A/B 测试 |
| 性能不达标 | 低 | 中 | 优化算法、调整参数 |

### 进度风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 测试覆盖率不达标 | 低 | 中 | TDD、提前编写测试 |
| 集成问题耗时 | 中 | 高 | 持续集成、早发现问题 |
| 性能优化耗时 | 中 | 中 | 设定明确目标、及时止损 |

---

## 📈 进度跟踪

### 每日站会

**时间**: 每日 09:00, 13:00, 18:00

**内容**:
- 上午：确认当日任务
- 下午：检查上午进度
- 晚上：总结当日成果

### 里程碑

| 里程碑 | 预计时间 | 状态 |
|--------|---------|------|
| 缓存层实现完成 | Day 1 12:00 | ☐ |
| 缓存层测试完成 | Day 1 18:00 | ☐ |
| 路由层实现完成 | Day 2 12:00 | ☐ |
| 路由层测试完成 | Day 2 16:00 | ☐ |
| 融合层实现完成 | Day 2 18:00 | ☐ |
| 集成测试完成 | Day 3 12:00 | ☐ |
| 性能测试完成 | Day 3 16:00 | ☐ |
| 文档完成 | Day 3 18:00 | ☐ |

---

## 📝 变更日志

| 日期 | 变更内容 | 作者 |
|------|---------|------|
| 2026-04-06 | 初稿创建 | AI 架构师 |

---

## 📚 参考文档

- [Phase 2 详细设计](./PHASE2-DESIGN-001.md)
- [Phase 1 查漏补缺报告](../phase1/PHASE1-GAP-001.md)
- [Phase 1 测试报告](../phase1/TEST-REPORT-001.md)
- [项目 README](../../README.md)

---

**计划制定时间**: 2026-04-06 12:35  
**作者**: AI 架构师  
**审批**: 张老师  
**状态**: ✅ 已批准，可开始实施

🦀 **Planning Excellence Achieved!** 🎉
