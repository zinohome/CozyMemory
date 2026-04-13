"""
API 补充测试

提高测试覆盖率至 85%+
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
async def test_query_memories(client):
    """测试查询记忆 - 修复版本"""
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
async def test_query_memories_with_type_filter(client):
    """测试按类型过滤查询"""
    # 创建不同类型记忆
    await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "咖啡偏好",
        "memory_type": "preference"
    })
    await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "事实信息",
        "memory_type": "fact"
    })
    
    # 按类型过滤
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "user_123", "memory_type": "preference", "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["memory_type"] == "preference"


@pytest.mark.asyncio
async def test_query_memories_invalid_type(client):
    """测试无效记忆类型"""
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "user_123", "memory_type": "invalid_type", "limit": 10}
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_query_memories_with_search(client):
    """测试带搜索的查询"""
    # 创建记忆
    await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "用户喜欢咖啡",
        "memory_type": "preference"
    })
    await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "用户喜欢茶",
        "memory_type": "preference"
    })
    
    # 搜索
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "user_123", "q": "咖啡", "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert "咖啡" in data["data"][0]["content"]


@pytest.mark.asyncio
async def test_query_memories_limit(client):
    """测试查询数量限制"""
    # 创建 20 条记忆
    for i in range(20):
        await client.post("/api/v1/memories", json={
            "user_id": "user_123",
            "content": f"内容 {i}",
            "memory_type": "fact"
        })
    
    # 限制返回 5 条
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "user_123", "limit": 5}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 5
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_query_memories_no_user(client):
    """测试无用户记忆"""
    response = await client.get(
        "/api/v1/memories",
        params={"user_id": "non_existent_user", "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 0
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_update_memory_not_found(client):
    """测试更新不存在的记忆"""
    response = await client.put(
        "/api/v1/memories/non_existent",
        json={"content": "新内容"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_memory_partial(client):
    """测试部分更新记忆"""
    # 创建记忆
    create_response = await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "原始内容",
        "memory_type": "fact",
        "metadata": {"key": "value"}
    })
    memory_id = create_response.json()["data"]["id"]
    
    # 只更新内容
    response = await client.put(
        f"/api/v1/memories/{memory_id}",
        json={"content": "新内容"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["content"] == "新内容"
    assert data["data"]["metadata"] == {"key": "value"}  # 元数据保留
    
    # 只更新元数据
    response2 = await client.put(
        f"/api/v1/memories/{memory_id}",
        json={"metadata": {"updated": True}}
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["data"]["content"] == "新内容"  # 内容保留
    assert data2["data"]["metadata"] == {"updated": True}


@pytest.mark.asyncio
async def test_delete_memory_not_found(client):
    """测试删除不存在的记忆"""
    response = await client.delete("/api/v1/memories/non_existent")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_create_empty(client):
    """测试批量创建空列表"""
    response = await client.post("/api/v1/memories/batch", json=[])
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_batch_create_single(client):
    """测试批量创建单条"""
    payloads = [{
        "user_id": "user_123",
        "content": "单条内容",
        "memory_type": "fact"
    }]
    
    response = await client.post("/api/v1/memories/batch", json=payloads)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_health_check_detailed(client):
    """测试详细健康检查"""
    response = await client.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert "engines" in data


@pytest.mark.asyncio
async def test_root_detailed(client):
    """测试根路径详细信息"""
    response = await client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CozyMemory"
    assert "version" in data
    assert "description" in data
    assert "docs" in data
    assert "health" in data


@pytest.mark.asyncio
async def test_create_memory_minimal(client):
    """测试创建最小化记忆"""
    # 只提供必需字段
    payload = {
        "user_id": "user_123",
        "content": "最小化记忆"
    }
    
    response = await client.post("/api/v1/memories", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["memory_type"] == "fact"  # 默认类型


@pytest.mark.asyncio
async def test_create_memory_all_types(client):
    """测试创建所有类型的记忆"""
    types = ["fact", "event", "preference", "skill", "conversation"]
    
    for mem_type in types:
        response = await client.post("/api/v1/memories", json={
            "user_id": "user_123",
            "content": f"{mem_type} 类型记忆",
            "memory_type": mem_type
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["memory_type"] == mem_type


@pytest.mark.asyncio
async def test_crud_lifecycle(client):
    """测试完整的 CRUD 生命周期"""
    # Create
    create_response = await client.post("/api/v1/memories", json={
        "user_id": "user_123",
        "content": "生命周期测试",
        "memory_type": "fact"
    })
    assert create_response.status_code == 200
    memory_id = create_response.json()["data"]["id"]
    
    # Read
    read_response = await client.get(f"/api/v1/memories/{memory_id}")
    assert read_response.status_code == 200
    assert read_response.json()["data"]["content"] == "生命周期测试"
    
    # Update
    update_response = await client.put(
        f"/api/v1/memories/{memory_id}",
        json={"content": "更新后的内容"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["content"] == "更新后的内容"
    
    # Delete
    delete_response = await client.delete(f"/api/v1/memories/{memory_id}")
    assert delete_response.status_code == 200
    
    # Verify deleted
    verify_response = await client.get(f"/api/v1/memories/{memory_id}")
    assert verify_response.status_code == 404
