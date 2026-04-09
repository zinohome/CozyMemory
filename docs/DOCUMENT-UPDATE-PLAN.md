# CozyMemory v0.2 文档更新计划

**日期**: 2026-04-09  
**版本**: v0.2 (简化版)  
**状态**: 待更新

---

## 📊 文档分类

### ✅ 已更新/新创建 (3 个)

| 文档 | 状态 | 说明 |
|------|------|------|
| `README.md` | ✅ 已完成 | v0.2 定位和快速开始 |
| `docs/SIMPLIFIED-REPORT.md` | ✅ 已完成 | v0.2 实现报告 |
| `docs/DESIGN-GAP-ANALYSIS.md` | ✅ 已完成 | 设计偏差分析 |

---

### 🔄 需要更新 (12 个 - 核心文档)

#### 架构文档 (6 个)

| 文档 | 更新内容 | 优先级 |
|------|---------|--------|
| `docs/architecture/00-architecture-vision.md` | 重新定位：从平台到库 | P0 |
| `docs/architecture/03-application-architecture.md` | 简化架构：2 层而非 5 层 | P0 |
| `docs/architecture/04-technology-architecture.md` | 技术栈简化：移除 PG/Redis/gRPC | P0 |
| `docs/architecture/00-architecture-summary.md` | 更新架构图和组件 | P0 |
| `docs/architecture/05-implementation-plan.md` | 更新实施计划 | P1 |
| `docs/architecture/07-memory-engine-analysis.md` | 更新引擎分析 | P1 |

#### ADR 架构决策 (4 个)

| 文档 | 更新内容 | 优先级 |
|------|---------|--------|
| `docs/architecture/adr/ADR-001-api-gateway.md` | 改为：不需要 API Gateway | P0 |
| `docs/architecture/adr/ADR-002-graphql.md` | 改为：不需要 GraphQL | P0 |
| `docs/architecture/adr/ADR-003-grpc.md` | 改为：不需要 gRPC | P0 |
| `docs/architecture/adr/ADR-004-routing.md` | 更新：关键词路由而非 LLM | P1 |

#### 开发指南 (2 个)

| 文档 | 更新内容 | 优先级 |
|------|---------|--------|
| `docs/dev/LOCAL-DEV-GUIDE.md` | 更新本地开发流程 | P0 |
| `docs/deployment.md` | 更新部署方式：pip install | P0 |

---

### 🗑️ 需要归档/删除 (27 个 - 过时文档)

#### Phase 1/2/3 报告 (14 个)

这些是基于旧架构的开发日志，已不适用：

- `docs/phase1/REPORT-001.md`
- `docs/phase1/TEST-REPORT-001.md`
- `docs/phase1/PHASE1-GAP-001.md`
- `docs/phase2/PHASE2-KICKOFF-001.md`
- `docs/phase2/PHASE2-PLAN-001.md`
- `docs/phase2/PHASE2-DESIGN-001.md`
- `docs/phase2/PHASE2-DAY1-001.md`
- `docs/phase2/PHASE2-DAY2-001.md`
- `docs/phase2/PHASE2-DAY3-001.md`
- `docs/phase2/PHASE2-SUMMARY-001.md`
- `docs/phase2/PERF-BENCHMARK-001.md`
- `docs/phase3/PHASE3-PLAN-001.md`
- `docs/phase3/PHASE3-DAY1-001.md`
- `docs/phase3/PHASE3-DAY2-001.md`
- `docs/phase3/PHASE3-DAY2-PLAN.md`

#### 过时架构文档 (8 个)

- `docs/architecture/01-business-architecture.md` (业务架构 - 过重)
- `docs/architecture/02-data-architecture.md` (数据架构 - PG/Redis)
- `docs/architecture/06-quality-assurance-plan.md` (QA 计划 - 过时)
- `docs/architecture/08-memory-engine-deep-analysis.md` (引擎深析 - 过时)
- `docs/architecture/adr/ADR-005-auth.md` (认证 - 不需要)
- `docs/arch/ADR-006-memory-optimization.md` (优化 - 不适用)
- `docs/ops/01-cicd-guide.md` (CI/CD - 不需要)
- `docs/dev/DEV-STD-001.md` (开发标准 - 需重写)

#### 项目管理文档 (5 个)

- `docs/pm/01-project-plan.md`
- `docs/pm/02-wbs.md`
- `docs/pm/03-progress-tracking.md`
- `docs/qa/01-test-plan.md`
- `docs/PROGRESS.md`

---

## 📋 更新策略

### 方案 A: 彻底清理 (推荐)

```bash
# 1. 创建归档目录
mkdir -p docs/archive/v0.1-oversigned

# 2. 移动过时文档
mv docs/phase1 docs/archive/v0.1-oversigned/
mv docs/phase2 docs/archive/v0.1-oversigned/
mv docs/phase3 docs/archive/v0.1-oversigned/
mv docs/architecture docs/archive/v0.1-oversigned/
mv docs/arch docs/archive/v0.1-oversigned/
mv docs/ops docs/archive/v0.1-oversigned/
mv docs/pm docs/archive/v0.1-oversigned/
mv docs/qa docs/archive/v0.1-oversigned/

# 3. 更新核心文档
# (手动更新 12 个 P0/P1 文档)

# 4. 创建新的文档结构
mkdir -p docs/architecture
mkdir -p docs/guides
mkdir -p docs/api
```

**优点**: 
- 清晰区分 v0.1 和 v0.2
- 新文档结构简洁
- 避免混淆

**缺点**: 
- 历史记录移动
- 需要更新引用链接

---

### 方案 B: 增量更新

```bash
# 1. 保留所有文档
# 2. 在文档顶部添加版本标记
# 3. 逐个更新核心文档
# 4. 过时文档标记为 [DEPRECATED]
```

**优点**: 
- 保留完整历史
- 无需移动文件

**缺点**: 
- 文档数量多 (42 个)
- 容易混淆版本

---

## 🎯 推荐执行计划

### Step 1: 创建新文档结构 (30 分钟)

```
docs/
├── architecture/          # 架构文档
│   ├── 00-vision.md      # 愿景 (更新)
│   ├── 01-architecture.md # 架构 (更新)
│   └── decisions/         # 架构决策
│       ├── 001-no-gateway.md
│       ├── 002-library-not-platform.md
│       └── 003-integration-first.md
├── guides/                # 使用指南
│   ├── getting-started.md
│   ├── configuration.md
│   └── adapters.md
├── api/                   # API 文档
│   └── reference.md
├── dev/                   # 开发指南
│   ├── local-dev.md
│   └── testing.md
└── archive/               # 归档 (v0.1)
    └── v0.1-oversigned/
```

### Step 2: 更新核心文档 (2 小时)

1. ✅ `README.md` - 已完成
2. 🔄 `docs/architecture/00-vision.md` - 重新定位
3. 🔄 `docs/architecture/01-architecture.md` - 新架构图
4. 🔄 `docs/guides/getting-started.md` - 快速开始
5. 🔄 `docs/guides/configuration.md` - 配置说明
6. 🔄 `docs/dev/local-dev.md` - 本地开发

### Step 3: 创建 API 文档 (1 小时)

- API 参考
- 使用示例
- 适配器文档

### Step 4: 归档旧文档 (30 分钟)

- 移动 v0.1 文档到 archive/
- 添加归档说明

---

## ⏱️ 时间估算

| 任务 | 时间 |
|------|------|
| 创建新结构 | 30 分钟 |
| 更新核心文档 | 2 小时 |
| 创建 API 文档 | 1 小时 |
| 归档旧文档 | 30 分钟 |
| **总计** | **4 小时** |

---

## 📝 文档更新清单

### P0 - 必须更新 (6 个)

- [ ] `docs/architecture/00-vision.md`
- [ ] `docs/architecture/01-architecture.md`
- [ ] `docs/guides/getting-started.md`
- [ ] `docs/guides/configuration.md`
- [ ] `docs/dev/local-dev.md`
- [ ] `docs/deployment.md`

### P1 - 应该更新 (6 个)

- [ ] `docs/architecture/decisions/001-no-gateway.md`
- [ ] `docs/architecture/decisions/002-library-not-platform.md`
- [ ] `docs/architecture/decisions/003-integration-first.md`
- [ ] `docs/guides/adapters.md`
- [ ] `docs/api/reference.md`
- [ ] `docs/dev/testing.md`

### P2 - 可选更新 (3 个)

- [ ] `docs/guides/router.md`
- [ ] `docs/guides/cache.md`
- [ ] `docs/faq.md`

---

## 🦀 建议

**张老师，我建议:**

1. **采用方案 A (彻底清理)** - 长痛不如短痛
2. **先更新 P0 文档 (6 个)** - 保证核心文档准确
3. **归档而非删除** - 保留历史记录
4. **创建简洁新结构** - 避免再次过度设计

**现在执行吗？还是先看看具体要更新哪些内容？** 🤔
