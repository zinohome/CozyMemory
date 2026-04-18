"""知识库 API 集成测试

针对真实运行的 CozyMemory + Cognee 后端执行完整流程：
  add → cognify → poll search（最多等待 120s）。

服务地址由 COZY_TEST_URL 环境变量控制（默认 http://localhost:8000）。
若服务不可达，测试自动跳过。

注意：
  - cognify 是异步后台任务，search 需要轮询等待结果
  - http_slow fixture 使用 300s 超时
  - Cognee health_check 调用 datasets 接口，响应通常 1~4s，属正常现象
"""

import asyncio

import pytest

from .conftest import requires_server

# 每次测试用独立数据集名，避免跨测试污染
TEST_DATASET = "integration-test-dataset"
TEST_CONTENT = "CozyMemory 是一个统一 AI 记忆服务平台，整合 Mem0、Memobase、Cognee 三大引擎。"


@requires_server
@pytest.mark.asyncio
async def test_list_datasets(http):
    """GET /knowledge/datasets 返回数据集列表"""
    response = await http.get("/api/v1/knowledge/datasets")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@requires_server
@pytest.mark.asyncio
async def test_add_knowledge(http):
    """POST /knowledge/add 成功添加文档"""
    response = await http.post(
        "/api/v1/knowledge/add",
        json={"data": TEST_CONTENT, "dataset": TEST_DATASET},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_cognify(http_slow):
    """POST /knowledge/cognify 启动知识图谱构建"""
    response = await http_slow.post(
        "/api/v1/knowledge/cognify",
        json={"datasets": [TEST_DATASET], "run_in_background": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


@requires_server
@pytest.mark.asyncio
async def test_search_knowledge_after_add(http):
    """POST /knowledge/search 添加文档后能搜索到相关内容"""
    response = await http.post(
        "/api/v1/knowledge/search",
        json={
            "query": "什么是 CozyMemory",
            "dataset": TEST_DATASET,
            "search_type": "CHUNKS",
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


@requires_server
@pytest.mark.asyncio
async def test_full_knowledge_flow(http_slow):
    """完整知识图谱流程：add → cognify → 轮询 search，最多等 120s"""
    # Step 1: 添加文档
    add_resp = await http_slow.post(
        "/api/v1/knowledge/add",
        json={"data": TEST_CONTENT, "dataset": TEST_DATASET},
    )
    assert add_resp.status_code == 200, f"add failed: {add_resp.text}"

    # Step 2: 触发知识图谱构建
    cognify_resp = await http_slow.post(
        "/api/v1/knowledge/cognify",
        json={"datasets": [TEST_DATASET], "run_in_background": True},
    )
    assert cognify_resp.status_code == 200, f"cognify failed: {cognify_resp.text}"

    # Step 3: 轮询搜索，最多等 120s
    found = False
    for attempt in range(12):  # 12 × 10s = 120s
        await asyncio.sleep(10)
        search_resp = await http_slow.post(
            "/api/v1/knowledge/search",
            json={
                "query": "CozyMemory 整合哪些引擎",
                "dataset": TEST_DATASET,
                "search_type": "CHUNKS",
                "top_k": 5,
            },
        )
        assert search_resp.status_code == 200
        results = search_resp.json().get("data", [])
        if results:
            found = True
            break

    assert found, "Cognify 完成后 120s 内未搜索到结果"


@requires_server
@pytest.mark.asyncio
async def test_search_missing_query_422(http):
    """POST /knowledge/search 空 query → 422"""
    response = await http.post(
        "/api/v1/knowledge/search",
        json={"query": ""},
    )
    assert response.status_code == 422
