"""
API 测试

测试 RESTful API 端点。
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.main import app
from src.adapters.memobase_mock_adapter import MemobaseMockAdapter


@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_mock_data():
    """每个测试前清空 Mock 数据"""
    MemobaseMockAdapter.clear_all()
    yield


@pytest.mark.asyncio
async def test_root(client):
    """测试根路径"""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CozyMemory"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check(client):
    """测试健康检查"""
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "engines" in data


@pytest.mark.asyncio
async def test_create_memory(client):
    """测试创建记忆"""
    payload = {
        "user_id": "user_123",
        "content": "用户喜欢喝拿铁咖啡",
        "memory_type": "preference",
        "metadata": {"source": "chat"}
    }
    
    response = await client.post("/api/v1/memories", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == "user_123"
    assert data["data"]["content"] == "用户喜欢喝拿铁咖啡"
    assert data["data"]["memory_type"] == "preference"


@pytest.mark.asyncio
async def test_create_memory_validation(client):
    """测试创建记忆的输入验证"""
    # 缺少 user_id
    payload = {
        "content": "测试内容",
        "memory_type": "fact"
    }
    
    response = await client.post("/api/v1/memories", json=payload)
    
    assert response.status_code == 422  # Validation Error


@pytest.mark.asyncio
async def test_get_memory(client):
    """测试获取记忆"""
    # 先创建
    create_payload = {
        "user_id": "user_123",
        "content": "测试内容",
        "memory_type": "fact"
    }
    create_response = await client.post("/api/v1/memories", json=create_payload)
    memory_id = create_response.json()["data"]["id"]
    
    # 再获取
    response = await client.get(f"/api/v1/memories/{memory_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == memory_id


@pytest.mark.asyncio
async def test_get_memory_not_found(client):
    """测试获取不存在的记忆"""
    response = await client.get("/api/v1/memories/non_existent")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_query_memories(client):
    """测试查询记忆"""
    # 创建多条记忆
    for i in range(5):
        await client.post("/api/v1/memories", json={
            "user_id": "user_123",
            "content": f"测试内容 {i}",
            "memory_type": "fact"
        })
    
    # 查询
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "user_123", "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 5
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_update_memory(client):
    """测试更新记忆"""
    # 创建
    create_response = await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "原始内容",
        "memory_type": "fact"
    })
    memory_id = create_response.json()["data"]["id"]
    
    # 更新
    update_payload = {
        "content": "更新后的内容",
        "metadata": {"updated": True}
    }
    response = await client.put(
        f"/api/v1/memories/{memory_id}",
        json=update_payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["content"] == "更新后的内容"


@pytest.mark.asyncio
async def test_delete_memory(client):
    """测试删除记忆"""
    # 创建
    create_response = await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "待删除",
        "memory_type": "fact"
    })
    memory_id = create_response.json()["data"]["id"]
    
    # 删除
    response = await client.delete(f"/api/v1/memories/{memory_id}")
    
    assert response.status_code == 200
    assert response.json()["success"] is True
    
    # 验证已删除
    get_response = await client.get(f"/api/v1/memories/{memory_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_batch_create(client):
    """测试批量创建"""
    payloads = [
        {
            "user_id": "user_123",
            "content": f"批量内容 {i}",
            "memory_type": "fact"
        }
        for i in range(5)
    ]
    
    response = await client.post("/api/v1/memories/batch", json=payloads)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 5
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_batch_create_limit(client):
    """测试批量创建数量限制"""
    # 创建超过限制的数量
    payloads = [
        {
            "user_id": "user_123",
            "content": f"内容 {i}",
            "memory_type": "fact"
        }
        for i in range(150)
    ]
    
    response = await client.post("/api/v1/memories/batch", json=payloads)
    
    assert response.status_code == 400
