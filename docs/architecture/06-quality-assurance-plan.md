# 统一 AI 记忆服务平台 - 质量保证计划

**文档编号**: ARCH-QA-006  
**版本**: 2.0 (基于深入分析后修订)  
**状态**: 草案  
**创建日期**: 2026-04-05  
**作者**: 蟹小五 (AI 架构师)

---

## 1. 质量目标

### 1.1 质量维度

| 维度 | 目标 | 测量指标 |
|------|------|---------|
| **功能性** | 满足所有需求 | 需求覆盖率 100% |
| **可靠性** | 高可用 | 可用性 > 99.5% |
| **性能** | 低延迟 | P95 < 200ms |
| **安全性** | 无高危漏洞 | 0 严重漏洞 |
| **可维护性** | 易于修改 | 代码复杂度 < 25 |
| **可测试性** | 易于测试 | 覆盖率 > 70% |

---

## 2. 测试策略

### 2.1 测试金字塔

```
                    ┌─────────────┐
                   │  E2E Tests  │  10%
                  │─────────────│
                 │ Integration  │  20%
                │    Tests     │
               │──────────────│
              │  Unit Tests   │  70%
             │────────────────│
```

### 2.2 测试类型

| 测试类型 | 工具 | 覆盖率目标 | 执行频率 |
|---------|------|-----------|---------|
| 单元测试 | pytest | > 70% | 每次提交 |
| 集成测试 | pytest + httpx | > 50% | 每次提交 |
| API 测试 | pytest + requests | 100% API | 每天 |
| 性能测试 | wrk + locust | 关键路径 | 每周 |
| 安全测试 | bandit + zap | 100% 代码 | 每周 |
| E2E 测试 | playwright | 核心流程 | 每周 |

---

## 3. 单元测试

### 3.1 测试框架

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.database import Base, get_db

# 测试数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

### 3.2 测试用例示例

#### 3.2.1 记忆服务测试
```python
# tests/services/test_memory_service.py
import pytest
from unittest.mock import AsyncMock, patch

from src.services.memory_service import MemoryService
from src.schemas.memory import MemoryCreate

class TestMemoryService:
    
    @pytest.mark.asyncio
    async def test_store_memory_success(self, db_session):
        """测试成功存储记忆"""
        # Arrange
        service = MemoryService(...)
        memory_data = MemoryCreate(
            content="我喜欢 Python",
            memory_type="fact"
        )
        
        # Mock adapter
        with patch.object(service.mem0_adapter, 'store') as mock_store:
            mock_store.return_value = Memory(id="test-123", ...)
            
            # Act
            result = await service.store_memory(
                user_id="user-123",
                content=memory_data.content,
                memory_type=memory_data.memory_type
            )
            
            # Assert
            assert result.id == "test-123"
            mock_store.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_memory_invalid_type(self, db_session):
        """测试无效记忆类型"""
        service = MemoryService(...)
        
        with pytest.raises(ValueError) as exc_info:
            await service.store_memory(
                user_id="user-123",
                content="test",
                memory_type="invalid_type"
            )
        
        assert "Invalid memory type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_retrieve_memories_parallel(self, db_session):
        """测试并行查询多个引擎"""
        service = MemoryService(...)
        
        # Mock multiple adapters
        with patch.object(service.mem0_adapter, 'retrieve') as mock_mem0, \
             patch.object(service.memobase_adapter, 'retrieve') as mock_memobase:
            
            mock_mem0.return_value = [Memory(...)]
            mock_memobase.return_value = [Memory(...)]
            
            result = await service.retrieve_memories(
                user_id="user-123",
                query="Python",
                limit=10
            )
            
            # Verify parallel execution
            assert mock_mem0.called
            assert mock_memobase.called
            assert len(result) > 0
```

#### 3.2.2 路由服务测试
```python
# tests/services/test_router_service.py
import pytest

from src.routers.hybrid_router import HybridRouter
from src.routers.rule_router import RuleRouter

class TestRuleRouter:
    
    def test_route_user_preference(self):
        """测试用户偏好路由"""
        router = RuleRouter()
        
        result = router.classify("我喜欢 Python 编程")
        
        assert "mem0" in result.engines
        assert result.source == "rules"
        assert result.confidence == 0.8
    
    def test_route_knowledge_query(self):
        """测试知识查询路由"""
        router = RuleRouter()
        
        result = router.classify("帮我找一下 Python 文档")
        
        assert "cognee" in result.engines
        assert result.source == "rules"
    
    def test_route_default(self):
        """测试默认路由"""
        router = RuleRouter()
        
        result = router.classify("随机查询")
        
        assert result.engines == ["mem0", "cognee", "memobase"]
        assert result.source == "rules"

class TestHybridRouter:
    
    @pytest.mark.asyncio
    async def test_hybrid_routing_llm_available(self):
        """测试 LLM 可用时的混合路由"""
        router = HybridRouter(mode="hybrid", llm_router=MockLLMRouter())
        
        result = await router.route("我喜欢什么？")
        
        # LLM 置信度高，使用 LLM 结果
        if result.confidence >= 0.6:
            assert result.source == "llm"
        else:
            assert result.source == "rules"
    
    @pytest.mark.asyncio
    async def test_hybrid_routing_llm_unavailable(self):
        """测试 LLM 不可用时的降级"""
        router = HybridRouter(mode="hybrid", llm_router=None)
        
        result = await router.route("测试查询")
        
        assert result.source == "rules"
        assert result.llm_fallback == True
```

#### 3.2.3 融合服务测试
```python
# tests/services/test_fusion_service.py
import pytest

from src.services.fusion_service import FusionService
from src.schemas.memory import Memory

class TestFusionService:
    
    @pytest.mark.asyncio
    async def test_deduplicate_memories(self):
        """测试记忆去重"""
        service = FusionService()
        
        memories = [
            Memory(id="1", content="相同内容", source="mem0", ...),
            Memory(id="2", content="相同内容", source="memobase", ...),  # 重复
            Memory(id="3", content="不同内容", source="cognee", ...),
        ]
        
        unique = service._deduplicate(memories)
        
        assert len(unique) == 2  # 去重后应该只有 2 条
    
    @pytest.mark.asyncio
    async def test_score_memories(self):
        """测试记忆评分"""
        service = FusionService()
        
        memories = [
            Memory(content="高度相关", similarity=0.95, ...),
            Memory(content="低度相关", similarity=0.3, ...),
        ]
        
        scored = await service._score_memories(memories, query="测试")
        
        assert scored[0].score > scored[1].score
    
    @pytest.mark.asyncio
    async def test_merge_and_rank(self):
        """测试完整融合流程"""
        service = FusionService()
        
        # 模拟来自多个引擎的结果
        all_memories = [
            Memory(id="m1", content="结果 1", source="mem0", similarity=0.9),
            Memory(id="m2", content="结果 2", source="memobase", similarity=0.8),
            Memory(id="m3", content="结果 3", source="cognee", similarity=0.7),
            Memory(id="m1", content="结果 1", source="mem0", similarity=0.9),  # 重复
        ]
        
        result = await service.merge_and_rank(all_memories, query="测试", limit=2)
        
        assert len(result) == 2  # 截断到 limit
        assert result[0].score > result[1].score  # 按分数排序
```

---

## 4. 集成测试

### 4.1 API 集成测试

```python
# tests/integration/test_memories_api.py
import pytest
from fastapi.testclient import TestClient

class TestMemoriesAPI:
    
    def test_create_memory_authenticated(self, client, auth_headers):
        """测试认证用户创建记忆"""
        response = client.post(
            "/api/v1/memories",
            json={
                "content": "我喜欢 Python",
                "memory_type": "fact"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        assert "id" in response.json()
    
    def test_create_memory_unauthenticated(self, client):
        """测试未认证用户创建记忆"""
        response = client.post(
            "/api/v1/memories",
            json={"content": "test"}
        )
        
        assert response.status_code == 401
    
    def test_search_memories(self, client, auth_headers, create_test_memories):
        """测试搜索记忆"""
        # 先创建测试数据
        create_test_memories(count=5)
        
        response = client.get(
            "/api/v1/memories/search?query=Python",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert len(response.json()) > 0
    
    def test_delete_memory(self, client, auth_headers, create_test_memory):
        """测试删除记忆"""
        memory_id = create_test_memory()
        
        response = client.delete(
            f"/api/v1/memories/{memory_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # 验证已删除
        get_response = client.get(
            f"/api/v1/memories/{memory_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
```

### 4.2 引擎集成测试

```python
# tests/integration/test_engine_adapters.py
import pytest
import asyncio

from src.adapters.mem0_adapter import Mem0Adapter
from src.adapters.memobase_adapter import MemobaseAdapter
from src.adapters.cognee_adapter import CogneeAdapter

class TestMem0Adapter:
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        """测试 Mem0 存储和检索"""
        adapter = Mem0Adapter()
        
        # Store
        result = await adapter.store(
            user_id="test-user",
            content="我喜欢 Python 编程",
            metadata={"source": "test"}
        )
        
        assert result is not None
        
        # Retrieve
        memories = await adapter.retrieve(
            user_id="test-user",
            query="编程",
            limit=5
        )
        
        assert len(memories) > 0
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """测试带过滤的搜索"""
        adapter = Mem0Adapter()
        
        memories = await adapter.retrieve(
            user_id="test-user",
            query="Python",
            limit=5,
            filters={"metadata.source": "test"}
        )
        
        assert len(memories) > 0

class TestMemobaseAdapter:
    
    @pytest.mark.asyncio
    async def test_profile_management(self):
        """测试 Memobase 画像管理"""
        adapter = MemobaseAdapter()
        
        # Create user
        user_id = adapter.client.add_user({"name": "Test"})
        
        # Insert chat
        adapter.insert_chat(user_id, [
            {"role": "user", "content": "我喜欢 Python"}
        ])
        
        # Flush
        adapter.flush(user_id, sync=True)
        
        # Get profile
        profile = adapter.get_profile(user_id)
        
        assert profile is not None

class TestCogneeAdapter:
    
    @pytest.mark.asyncio
    async def test_knowledge_graph(self):
        """测试 Cognee 知识图谱"""
        adapter = CogneeAdapter()
        
        # Add document
        await adapter.add_document(
            user_id="test-user",
            content="Python 是一门编程语言"
        )
        
        # Build graph
        await adapter.cognify()
        
        # Search
        results = await adapter.search_knowledge(
            user_id="test-user",
            query="Python"
        )
        
        assert len(results) > 0
```

---

## 5. 性能测试

### 5.1 基准测试

```python
# tests/performance/benchmark.py
import asyncio
import time
import aiohttp
import statistics

class PerformanceBenchmark:
    
    async def benchmark_create_memory(self, iterations=100):
        """基准测试：创建记忆"""
        async with aiohttp.ClientSession() as session:
            latencies = []
            
            for _ in range(iterations):
                start = time.time()
                
                async with session.post(
                    "http://localhost:8000/api/v1/memories",
                    json={"content": "测试记忆", "memory_type": "fact"},
                    headers={"Authorization": "Bearer test-token"}
                ) as response:
                    await response.json()
                
                latencies.append(time.time() - start)
            
            return {
                "p50": statistics.median(latencies),
                "p95": sorted(latencies)[int(len(latencies) * 0.95)],
                "p99": sorted(latencies)[int(len(latencies) * 0.99)],
                "qps": iterations / sum(latencies)
            }
    
    async def benchmark_search_memory(self, iterations=100):
        """基准测试：搜索记忆"""
        async with aiohttp.ClientSession() as session:
            latencies = []
            
            for _ in range(iterations):
                start = time.time()
                
                async with session.get(
                    "http://localhost:8000/api/v1/memories/search?query=测试",
                    headers={"Authorization": "Bearer test-token"}
                ) as response:
                    await response.json()
                
                latencies.append(time.time() - start)
            
            return {
                "p50": statistics.median(latencies),
                "p95": sorted(latencies)[int(len(latencies) * 0.95)],
                "p99": sorted(latencies)[int(len(latencies) * 0.99)],
                "qps": iterations / sum(latencies)
            }

# 运行基准测试
async def main():
    benchmark = PerformanceBenchmark()
    
    create_result = await benchmark.benchmark_create_memory()
    print(f"Create Memory: P95={create_result['p95']*1000:.2f}ms, QPS={create_result['qps']:.2f}")
    
    search_result = await benchmark.benchmark_search_memory()
    print(f"Search Memory: P95={search_result['p95']*1000:.2f}ms, QPS={search_result['qps']:.2f}")

asyncio.run(main())
```

### 5.2 负载测试 (wrk)

```bash
# tests/performance/wrk/create_memory.lua
wrk.method = "POST"
wrk.url = "http://localhost:8000/api/v1/memories"
wrk.headers["Content-Type"] = "application/json"
wrk.headers["Authorization"] = "Bearer test-token"
wrk.body = '{"content": "测试记忆", "memory_type": "fact"}'

# 运行负载测试
wrk -t12 -c400 -d30s -s tests/performance/wrk/create_memory.lua

# 预期输出:
# Running 30s test @ http://localhost:8000/api/v1/memories
#   12 threads and 400 connections
#   Thread Stats   Avg      Stdev   Max   +/- Stdev
#     Latency   150.23ms   45.67ms   450.12ms   85.23%
#     Req/Sec   234.56     45.67     345.00     78.90%
#   7023 requests in 30s, 1.23MB read
#   Requests/sec: 234.10
```

### 5.3 压力测试 (locust)

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class MemoryUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """登录获取 token"""
        response = self.client.post("/auth/jwt/login", json={
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def search_memories(self):
        """搜索记忆 (高频操作)"""
        queries = ["Python", "编程", "学习", "工作"]
        query = random.choice(queries)
        
        self.client.get(
            f"/api/v1/memories/search?query={query}",
            headers=self.headers
        )
    
    @task(2)
    def create_memory(self):
        """创建记忆 (中频操作)"""
        self.client.post(
            "/api/v1/memories",
            json={"content": f"测试记忆 {random.randint(1, 1000)}", "memory_type": "fact"},
            headers=self.headers
        )
    
    @task(1)
    def get_profile(self):
        """获取画像 (低频操作)"""
        self.client.get("/api/v1/users/me", headers=self.headers)

# 运行压力测试
# locust -f tests/performance/locustfile.py --users 1000 --spawn-rate 100
```

---

## 6. 安全测试

### 6.1 静态代码分析

```bash
# 安全扫描
bandit -r src/ -f json -o reports/bandit-report.json

# 依赖漏洞扫描
safety check --json > reports/safety-report.json
pip-audit --format json > reports/pip-audit-report.json

# 代码质量检查
ruff check src/
mypy src/
```

### 6.2 动态安全测试

```python
# tests/security/test_security.py
import pytest
from fastapi.testclient import TestClient

class TestSecurity:
    
    def test_sql_injection(self, client):
        """测试 SQL 注入防护"""
        malicious_input = "'; DROP TABLE users; --"
        
        response = client.post(
            "/api/v1/memories",
            json={"content": malicious_input},
            headers={"Authorization": "Bearer test"}
        )
        
        # 应该正常处理，不报错
        assert response.status_code in [201, 400, 401]
    
    def test_xss_attack(self, client):
        """测试 XSS 攻击防护"""
        xss_payload = "<script>alert('XSS')</script>"
        
        response = client.post(
            "/api/v1/memories",
            json={"content": xss_payload},
            headers={"Authorization": "Bearer test"}
        )
        
        # 应该转义或拒绝
        assert response.status_code in [201, 400]
    
    def test_rate_limiting(self, client):
        """测试限流"""
        # 快速发送 100 个请求
        responses = []
        for _ in range(100):
            response = client.get("/api/v1/memories")
            responses.append(response.status_code)
        
        # 应该有请求被限流 (429)
        assert 429 in responses
    
    def test_authentication_bypass(self, client):
        """测试认证绕过"""
        # 尝试未认证访问
        response = client.get("/api/v1/memories")
        
        assert response.status_code == 401
```

---

## 7. 代码质量

### 7.1 代码规范

```yaml
# .ruff.yml
line-length: 100
target-version: "py313"

select:
  - E    # pycodestyle errors
  - W    # pycodestyle warnings
  - F    # pyflakes
  - I    # isort
  - B    # flake8-bugbear
  - C4   # flake8-comprehensions

ignore:
  - E501  # line too long (handled by formatter)

[per-file-ignores]
"__init__.py" = ["F401"]  # unused imports allowed in __init__.py
```

### 7.2 类型检查

```yaml
# mypy.ini
[mypy]
python_version = 3.13
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
```

### 7.3 代码审查清单

- [ ] 代码符合 PEP 8 规范
- [ ] 所有公共函数有类型注解
- [ ] 所有函数有 docstring
- [ ] 单元测试覆盖新功能
- [ ] 无安全漏洞
- [ ] 性能影响已评估
- [ ] 文档已更新

---

## 8. 持续集成

### 8.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run linters
        run: |
          ruff check src/
          mypy src/
      
      - name: Run security scans
        run: |
          bandit -r src/
          safety check
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 9. 质量度量

### 9.1 质量仪表板

| 指标 | 目标 | 当前值 | 状态 |
|------|------|--------|------|
| 代码覆盖率 | > 70% | 75% | ✅ |
| 技术债务率 | < 5% | 3.2% | ✅ |
| 平均代码复杂度 | < 25 | 18 | ✅ |
| 严重 Bug 数 | 0 | 0 | ✅ |
| 安全漏洞数 | 0 | 0 | ✅ |
| 构建成功率 | > 95% | 98% | ✅ |

### 9.2 质量门禁

```yaml
# 质量门禁配置
quality_gates:
  code_coverage:
    threshold: 70%
    action: block_merge
  
  security_vulnerabilities:
    threshold: 0
    action: block_merge
  
  code_complexity:
    threshold: 25
    action: warn
  
  test_failures:
    threshold: 0
    action: block_merge
```

---

## 10. 缺陷管理

### 10.1 缺陷分级

| 级别 | 描述 | 响应时间 | 修复时间 |
|------|------|---------|---------|
| **P0** | 系统崩溃/数据丢失 | 15 分钟 | 4 小时 |
| **P1** | 核心功能不可用 | 1 小时 | 24 小时 |
| **P2** | 非核心功能异常 | 4 小时 | 3 天 |
| **P3** | 轻微问题/优化建议 | 24 小时 | 1 周 |

### 10.2 缺陷流程

```
发现缺陷 → 记录 (Jira/GitHub) → 分级 → 分配 → 修复 → 验证 → 关闭
```

---

**END OF DOCUMENT**
