# CozyMemory 项目测试计划

**文档编号**: QA-PLAN-001  
**版本**: 1.0  
**创建日期**: 2026-04-05  
**测试经理**: 测试 Lead  
**关联文档**: [01-project-plan.md](./pm/01-project-plan.md), [02-wbs.md](./pm/02-wbs.md)

---

## 1. 测试概述

### 1.1 测试目标

本测试计划定义 CozyMemory 项目的测试策略、范围、资源、进度和交付物，确保：
- 功能符合需求规格
- 性能满足 SLA 要求 (P95 延迟 <200ms)
- 安全性通过审计 (0 高危漏洞)
- 可用性达到 99.9%

### 1.2 测试范围

**包含**:
- ✅ 统一 API 层功能测试
- ✅ 三大引擎适配器集成测试
- ✅ 缓存层性能测试
- ✅ 路由服务准确性测试
- ✅ 融合服务排序质量测试
- ✅ 安全漏洞扫描
- ✅ 压力测试 (1000 QPS)

**不包含**:
- ❌ 引擎本身测试 (由开源项目负责)
- ❌ 前端 UI 测试 (无 UI)
- ❌ 移动端 SDK 测试 (Phase 2)

### 1.3 测试类型

| 测试类型 | 目标 | 工具 | 负责人 |
|---------|------|------|--------|
| 单元测试 | 验证单个函数/类 | pytest | 测试 A |
| 集成测试 | 验证组件间交互 | pytest + httpx | 测试 B |
| 性能测试 | 验证延迟/吞吐量 | locust | Tech Lead |
| 安全测试 | 发现安全漏洞 | SonarQube + OWASP ZAP | 外部 |
| 验收测试 | 验证业务需求 | 手动测试 | PM |

---

## 2. 测试策略

### 2.1 测试金字塔

```
           /\
          /  \
         / E2E \        验收测试 (10%)
        /--------\      手动测试
       /          \
      / Integration \    集成测试 (20%)
     /----------------\  API 测试
    /                  \
   /     Unit Tests     \  单元测试 (70%)
  /----------------------\  pytest
```

### 2.2 测试层次

#### 2.2.1 单元测试 (Unit Testing)

**目标**: 验证单个函数/类的正确性

**范围**:
- 适配器层 (Memobase/Mem0/Cognee Adapter)
- 服务层 (Cache/Router/Fusion Service)
- 工具层 (Utils/Helpers)

**工具**: pytest + pytest-cov

**覆盖率要求**:
- 行覆盖率: >80%
- 分支覆盖率: >70%
- 函数覆盖率: >90%

**示例**:
```python
# tests/unit/test_memobase_adapter.py
class TestMemobaseAdapter:
    def test_store_success(self, mock_memobase_client):
        adapter = MemobaseAdapter(api_key="test")
        result = await adapter.store(
            user_id="user_123",
            content="我喜欢 Python",
            metadata={"source": "chat"}
        )
        assert result.id is not None
        assert result.memory_type == "profile"
    
    def test_retrieve_empty(self, mock_memobase_client):
        adapter = MemobaseAdapter(api_key="test")
        results = await adapter.retrieve(
            user_id="user_456",
            query="编程偏好",
            limit=5
        )
        assert len(results) == 0
```

---

#### 2.2.2 集成测试 (Integration Testing)

**目标**: 验证组件间交互的正确性

**范围**:
- API → 适配器 → 引擎
- 缓存层 → Redis
- 路由服务 → 适配器
- 融合服务 → 多引擎

**工具**: pytest + httpx + TestContainer

**环境**: Docker Compose (隔离测试环境)

**示例**:
```python
# tests/integration/test_api.py
class TestMemoryAPI:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, test_client, redis_container):
        # 1. 存储记忆
        response = await test_client.post(
            "/api/v1/memories",
            json={
                "user_id": "user_123",
                "content": "我喜欢 Python 编程",
                "intent": "fact"
            }
        )
        assert response.status_code == 200
        memory_id = response.json()["id"]
        
        # 2. 检索记忆
        response = await test_client.get(
            f"/api/v1/memories/{memory_id}"
        )
        assert response.status_code == 200
        assert "Python" in response.json()["content"]
```

---

#### 2.2.3 性能测试 (Performance Testing)

**目标**: 验证系统在高负载下的性能表现

**指标**:
- P50 延迟: <100ms
- P95 延迟: <200ms
- P99 延迟: <500ms
- 吞吐量: >1000 QPS
- 错误率: <0.1%

**工具**: locust

**场景**:
1. **基准测试**: 单用户，测量基线延迟
2. **负载测试**: 100 并发用户，持续 10 分钟
3. **压力测试**: 逐步增加负载至系统崩溃
4. **耐久性测试**: 500 并发用户，持续 1 小时

**示例**:
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class MemoryUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    @task(3)
    def store_memory(self):
        self.client.post(
            "/api/v1/memories",
            json={
                "user_id": "user_123",
                "content": "测试记忆内容",
                "intent": "fact"
            }
        )
    
    @task(2)
    def retrieve_memory(self):
        self.client.get(
            "/api/v1/memories/search?query=测试&user_id=user_123"
        )
    
    @task(1)
    def hybrid_search(self):
        self.client.post(
            "/api/v1/search/hybrid",
            json={
                "user_id": "user_123",
                "query": "编程偏好",
                "limit": 10
            }
        )
```

**执行命令**:
```bash
# 基准测试
locust -f tests/performance/locustfile.py --headless -u 1 -r 1 --run-time 60s

# 负载测试 (100 并发)
locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 600s

# 压力测试 (逐步增加)
locust -f tests/performance/locustfile.py --headless -u 1000 -r 50 --run-time 1800s
```

---

#### 2.2.4 安全测试 (Security Testing)

**目标**: 发现并修复安全漏洞

**范围**:
- OWASP Top 10 漏洞扫描
- 依赖项漏洞扫描
- 代码静态分析
- 渗透测试

**工具**:
- SonarQube (代码质量 + 安全)
- OWASP ZAP (Web 应用扫描)
- safety (Python 依赖扫描)
- bandit (Python 代码扫描)

**流程**:
```
1. 代码提交 → SonarQube 扫描
2. 每日构建 → safety 依赖扫描
3. Phase 末 → OWASP ZAP 全面扫描
4. 上线前 → 外部安全审计
```

**验收标准**:
- 0 高危漏洞
- <5 中危漏洞
- 所有漏洞有修复计划

---

#### 2.2.5 验收测试 (User Acceptance Testing)

**目标**: 验证系统满足业务需求

**范围**:
- Phase 1: Memobase 功能验收
- Phase 2: Mem0 功能验收
- Phase 3: Cognee 功能验收
- Phase 4: 整体验收

**参与者**:
- 产品经理 (PM)
- 业务代表 (张老师)
- 最终用户代表

**测试用例示例**:
```
用例 ID: UAT-001
名称: 用户画像存储与检索
前置条件: Memobase 引擎已部署
步骤:
  1. 调用 API 存储用户偏好
  2. 调用 API 检索用户画像
  3. 验证返回内容正确
预期结果:
  - 存储成功，返回 memory_id
  - 检索成功，返回结构化画像
  - 画像内容与实际存储一致
```

---

## 3. 测试环境

### 3.1 环境配置

| 环境 | 用途 | 配置 | 负责人 |
|------|------|------|--------|
| 开发环境 | 单元测试 | Docker Compose (本地) | 开发 |
| 测试环境 | 集成测试 | Docker Compose (独立) | 测试 |
| Staging | 性能/UAT | Kubernetes (1:1 生产) | 运维 |
| 生产 | 线上服务 | Kubernetes (多副本) | 运维 |

### 3.2 测试数据

**数据生成策略**:
- 单元测试: Mock 数据
- 集成测试: TestContainer 动态生成
- 性能测试: Faker 生成 10 万条记录
- 验收测试: 真实业务数据 (脱敏)

**数据清理**:
- 每次测试后自动清理
- 使用事务回滚
- Docker 容器销毁

---

## 4. 测试进度

### 4.1 测试里程碑

| 里程碑 | 日期 | 关联任务 | 交付物 |
|--------|------|---------|--------|
| T0 | 2026-04-18 | 1.5.1 | 测试计划 |
| T1 | 2026-04-25 | 1.5.2 | 测试用例集 |
| T2 | 2026-05-02 | 1.4.2.4-5 | Memobase 测试报告 |
| T3 | 2026-05-23 | 1.4.3.6-7 | Mem0 测试报告 |
| T4 | 2026-06-13 | 1.4.4.6-7 | Cognee 测试报告 |
| T5 | 2026-06-20 | 1.4.5.1 | 压力测试报告 |
| T6 | 2026-06-25 | 1.4.5.3 | 安全审计报告 |
| T7 | 2026-06-28 | 1.5.10 | 测试总结报告 |

### 4.2 测试执行计划

```
Phase 1 (Memobase):
├── 单元测试：2026-04-26 ~ 2026-04-28 (3 天)
├── 集成测试：2026-04-29 ~ 2026-05-01 (3 天)
└── UAT: 2026-05-02 (2 天)

Phase 2 (Mem0):
├── 单元测试：2026-05-09 ~ 2026-05-11 (3 天)
├── 集成测试：2026-05-12 ~ 2026-05-14 (3 天)
├── 性能测试：2026-05-15 ~ 2026-05-17 (3 天)
└── UAT: 2026-05-18 (2 天)

Phase 3 (Cognee):
├── 单元测试：2026-06-02 ~ 2026-06-04 (3 天)
├── 集成测试：2026-06-05 ~ 2026-06-07 (3 天)
└── UAT: 2026-06-08 (2 天)

Phase 4 (优化):
├── 压力测试：2026-06-14 ~ 2026-06-16 (3 天)
├── 安全测试：2026-06-17 ~ 2026-06-19 (3 天)
└── 测试总结：2026-06-20 (2 天)
```

---

## 5. 缺陷管理

### 5.1 缺陷分级

| 级别 | 定义 | 响应时间 | 修复时限 |
|------|------|---------|---------|
| P0 - 致命 | 系统崩溃/数据丢失 | 1 小时 | 24 小时 |
| P1 - 严重 | 核心功能不可用 | 4 小时 | 3 天 |
| P2 - 一般 | 非核心功能异常 | 1 天 | 1 周 |
| P3 - 轻微 | UI/体验问题 | 1 周 | 下个迭代 |

### 5.2 缺陷流程

```
发现缺陷
    ↓
提交 Jira (包含：标题/描述/步骤/截图/日志)
    ↓
测试 Lead 确认 + 分级
    ↓
分配给开发负责人
    ↓
开发修复 + 单元测试
    ↓
测试验证
├── 通过 → 关闭
└── 失败 → 重新打开
```

### 5.3 缺陷度量

| 指标 | 目标值 |
|------|--------|
| 缺陷发现率 | >5 缺陷/千行代码 |
| 缺陷修复率 | >95% |
| 缺陷重开率 | <5% |
| 平均修复时间 | <3 天 |

---

## 6. 测试交付物

### 6.1 交付物清单

| 交付物 | 格式 | 位置 | 负责人 |
|--------|------|------|--------|
| 测试计划 | Markdown | `docs/qa/01-test-plan.md` | 测试 Lead |
| 测试用例 | Markdown/Excel | `docs/qa/test-cases/` | 测试 A/B |
| 测试脚本 | Python | `tests/` | 测试 A/B |
| 测试报告 | Markdown | `docs/qa/reports/` | 测试 Lead |
| 缺陷报告 | Jira | Jira 项目 | 测试 Lead |
| 性能报告 | Markdown | `docs/qa/perf-reports/` | Tech Lead |
| 安全报告 | PDF | `docs/qa/security/` | 外部 |
| 测试总结 | Markdown | `docs/qa/09-test-summary.md` | 测试 Lead |

### 6.2 测试报告模板

```markdown
## 测试报告 (Phase X)

### 测试概况
- 测试周期：YYYY-MM-DD ~ YYYY-MM-DD
- 测试类型：单元/集成/性能/安全
- 测试人员：XXX

### 测试结果
| 测试类型 | 用例数 | 通过 | 失败 | 通过率 |
|---------|--------|------|------|--------|
| 单元测试 | 200 | 198 | 2 | 99% |
| 集成测试 | 50 | 48 | 2 | 96% |
| 性能测试 | 10 | 10 | 0 | 100% |

### 缺陷统计
| 级别 | 新增 | 修复 | 遗留 |
|------|------|------|------|
| P0 | 0 | 0 | 0 |
| P1 | 2 | 2 | 0 |
| P2 | 5 | 4 | 1 |
| P3 | 10 | 8 | 2 |

### 性能指标
| 指标 | 目标值 | 实测值 | 状态 |
|------|--------|--------|------|
| P95 延迟 | <200ms | 180ms | ✅ |
| 吞吐量 | >1000 QPS | 1200 QPS | ✅ |
| 错误率 | <0.1% | 0.05% | ✅ |

### 风险评估
- 遗留缺陷影响：低
- 性能风险：无
- 上线建议：✅ 建议上线

### 附录
- 测试日志：[链接]
- 缺陷列表：[Jira 链接]
```

---

## 7. 工具与资源

### 7.1 测试工具栈

```
测试框架: pytest + pytest-asyncio + pytest-cov
API 测试：httpx + TestContainer
性能测试：locust
安全扫描：SonarQube + OWASP ZAP + safety + bandit
CI/CD: GitHub Actions
缺陷管理：Jira
文档：Markdown + Notion
```

### 7.2 硬件资源

| 环境 | CPU | 内存 | 存储 | 数量 |
|------|-----|------|------|------|
| 测试环境 | 4 核 | 8GB | 50GB | 2 |
| Staging | 8 核 | 16GB | 100GB | 3 |
| 性能测试 | 16 核 | 32GB | 200GB | 1 |

---

## 8. 风险与缓解

### 8.1 测试风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| 测试环境不稳定 | 高 | 中 | 使用 Docker Compose 隔离 |
| 测试数据不足 | 中 | 中 | Faker 生成 + 生产数据脱敏 |
| 性能测试资源不足 | 中 | 低 | 提前申请云资源 |
| 安全审计延期 | 高 | 低 | 提前预约外部审计 |

---

## 9. 附录

### 9.1 参考文档

- [ISTQB 测试基础大纲](https://www.istqb.org/)
- [Google 测试方法论](https://testing.googleblog.com/)
- [pytest 官方文档](https://docs.pytest.org/)
- [locust 官方文档](https://docs.locust.io/)

### 9.2 术语表

| 术语 | 定义 |
|------|------|
| QPS | Queries Per Second (每秒查询数) |
| P95 | 95th Percentile (95% 的请求低于此值) |
| SLA | Service Level Agreement (服务等级协议) |
| UAT | User Acceptance Testing (用户验收测试) |

---

**审批**

| 角色 | 姓名 | 签字 | 日期 |
|------|------|------|------|
| 测试经理 | | | 2026-04-05 |
| 项目经理 | AI 架构师 | | 2026-04-05 |
| 技术负责人 | | | |

---

**版本历史**

| 版本 | 日期 | 作者 | 变更描述 |
|------|------|------|---------|
| 1.0 | 2026-04-05 | AI 架构师 | 初始版本 |
