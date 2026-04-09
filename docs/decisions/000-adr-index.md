# 架构决策记录 (ADR)

**版本**: v0.2  
**日期**: 2026-04-09

---

## ADR-001: 库而非平台

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

v0.1 版本设计为独立平台，需要：
- API Gateway
- 数据库 (PostgreSQL)
- 缓存 (Redis)
- 独立部署

这导致：
- 部署复杂
- 运维成本高
- 用户门槛高

### 决策

**将 CozyMemory 定位为 Python 库，而非独立平台。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **平台** | - 独立演进<br>- 语言无关 | - 部署复杂<br>- 运维成本高<br>- 用户门槛高 |
| **库** | - 简单部署<br>- 零运维<br>- 低门槛 | - 绑定 Python<br>- 依赖管理 |

### 后果

**正面**:
- ✅ `pip install` 即可使用
- ✅ 无需 Docker/K8s
- ✅ 快速集成到现有项目
- ✅ 降低用户门槛

**负面**:
- ⚠️ 仅限 Python 生态
- ⚠️ 需要处理依赖冲突
- ⚠️ 版本升级需用户配合

### 实施

```python
# 使用方式
from cozy_memory import MemoryService

service = MemoryService()
await service.add("用户喜欢咖啡")
```

---

## ADR-002: 不需要 API Gateway

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

传统微服务架构中，API Gateway 提供：
- 路由
- 认证
- 限流
- 日志

但 CozyMemory v0.2 是库，不是服务。

### 决策

**不实现 API Gateway，直接函数调用。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **有 Gateway** | - 统一入口<br>- 集中管理 | - 增加延迟<br>- 增加复杂度<br>- 需要部署 |
| **无 Gateway** | - 直接调用<br>- 零延迟<br>- 零部署 | - 无统一入口<br>- 分散管理 |

### 后果

**正面**:
- ✅ 调用延迟降低 ~10ms
- ✅ 无需维护 Gateway 服务
- ✅ 代码量减少 ~2000 行

**负面**:
- ⚠️ 需要在调用方处理认证
- ⚠️ 需要在调用方处理限流

### 实施

```python
# 直接调用
service = MemoryService(adapter=MemobaseAdapter(api_key="xxx"))
await service.add("记忆内容")

# 而非
# response = requests.post("http://gateway:8000/api/memories", ...)
```

---

## ADR-003: 不需要 GraphQL

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

GraphQL 提供：
- 灵活查询
- 类型系统
- 自动文档

但需要：
- Schema 定义
- Resolver 实现
- 额外学习成本

### 决策

**使用简单 Python API，不实现 GraphQL。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **GraphQL** | - 灵活查询<br>- 类型安全 | - 学习成本高<br>- 实现复杂<br>- 性能开销 |
| **Python API** | - 简单直接<br>- 零学习成本<br>- 性能好 | - 查询固定<br>- 需版本管理 |

### 后果

**正面**:
- ✅ API 直观易用
- ✅ 无需学习 GraphQL
- ✅ 性能更好 (无解析开销)

**负面**:
- ⚠️ 查询灵活性较低
- ⚠️ API 变更需版本升级

### 实施

```python
# 简单 API
memories = await service.search("咖啡", limit=10)

# 而非 GraphQL
# query = """
#   query { memories(query: "咖啡", limit: 10) { id content } }
# """
```

---

## ADR-004: 不需要 gRPC

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

gRPC 提供：
- 高性能 RPC
- 多语言支持
- 流式传输

但需要：
- Protocol Buffers 定义
- 代码生成
- 额外依赖

### 决策

**使用直接函数调用，不实现 gRPC。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **gRPC** | - 高性能<br>- 多语言 | - 实现复杂<br>- 需要编译<br>- 依赖重 |
| **直接调用** | - 简单<br>- 零配置<br>- 轻量 | - 仅限进程内<br>- 无流式 |

### 后果

**正面**:
- ✅ 零配置
- ✅ 无编译步骤
- ✅ 依赖轻量

**负面**:
- ⚠️ 无法跨进程调用
- ⚠️ 无法流式传输

### 实施

```python
# 直接调用
result = await service.add("记忆")

# 而非 gRPC
# stub = MemoryServiceStub(channel)
# response = await stub.Add(AddRequest(content="记忆"))
```

---

## ADR-005: 关键词路由而非 LLM 路由

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

智能路由可使用：
- LLM 意图识别 (准确但贵)
- 关键词匹配 (简单但有限)
- 混合方案

### 决策

**优先使用关键词路由，LLM 路由作为可选扩展。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **LLM 路由** | - 准确<br>- 灵活 | - 成本高<br>- 延迟高<br>- 依赖外部 API |
| **关键词路由** | - 零成本<br>- 零延迟<br>- 离线可用 | - 准确性有限<br>- 需维护关键词 |

### 后果

**正面**:
- ✅ 零额外成本
- ✅ 零额外延迟
- ✅ 离线可用

**负面**:
- ⚠️ 复杂意图识别不准确
- ⚠️ 需维护关键词库

### 实施

```python
# 关键词路由
if "价格" in query or "费用" in query:
    adapter = pricing_adapter
elif "技术" in query or "代码" in query:
    adapter = tech_adapter
else:
    adapter = default_adapter

# 而非 LLM 路由
# intent = await llm.classify(query)
# adapter = router.get_adapter(intent)
```

---

## ADR-006: Mock 优先开发

**状态**: 已接受  
**日期**: 2026-04-09

### 背景

开发依赖外部服务 (Memobase) 导致：
- 需要 API Key
- 网络依赖
- 测试成本高
- CI/CD 复杂

### 决策

**提供 Mock 适配器，本地开发无需外部服务。**

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **依赖外部服务** | - 真实环境<br>- 集成测试 | - 需要 API Key<br>- 网络依赖<br>- 测试成本高 |
| **Mock 优先** | - 零配置<br>- 离线开发<br>- 快速测试 | - 非真实环境<br>- 需额外集成测试 |

### 后果

**正面**:
- ✅ 开箱即用
- ✅ 离线开发
- ✅ 测试快速 (<1s)
- ✅ CI/CD 简单

**负面**:
- ⚠️ 需要额外集成测试
- ⚠️ Mock 与真实环境可能有差异

### 实施

```python
# 默认使用 Mock
service = MemoryService()  # MemobaseMockAdapter

# 生产环境切换
service = MemoryService(adapter=MemobaseAdapter(api_key="xxx"))
```

---

## 🦀 维护者注释

**ADR 管理原则**:

1. **决策可追溯**: 每个重大决策都有记录
2. **背景清晰**: 说明为什么做这个决策
3. **后果明确**: 正面和负面后果都记录
4. **可撤销**: 如果情况变化，可以创建新 ADR 覆盖

**何时创建 ADR**:
- 架构变更
- 技术选型
- 重大重构
- 性能优化

**何时不创建 ADR**:
- Bug 修复
- 小功能添加
- 文档更新
- 代码重构 (不改变行为)

---

**最后更新**: 2026-04-09  
**维护者**: 蟹小五 🦀
