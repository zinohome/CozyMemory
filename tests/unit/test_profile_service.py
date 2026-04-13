"""用户画像服务测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.models.profile import (
    ProfileContext,
    ProfileTopic,
    UserProfile,
)
from cozymemory.services.profile import ProfileService


@pytest.fixture
def mock_memobase_client():
    client = MagicMock()
    client.insert = AsyncMock(return_value="blob_123")
    client.flush = AsyncMock(return_value=None)
    client.profile = AsyncMock(
        return_value=UserProfile(
            user_id="u1",
            topics=[ProfileTopic(id="p1", topic="basic_info", sub_topic="name", content="小明")],
        )
    )
    client.context = AsyncMock(return_value=ProfileContext(user_id="u1", context="# Memory\n..."))
    client.add_profile = AsyncMock(
        return_value=ProfileTopic(id="p2", topic="interest", sub_topic="hobby", content="游泳")
    )
    client.delete_profile = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_profile_service_insert(mock_memobase_client):
    service = ProfileService(client=mock_memobase_client)
    result = await service.insert(user_id="u1", messages=[{"role": "user", "content": "你好"}])
    assert result.success is True
    assert result.blob_id == "blob_123"


@pytest.mark.asyncio
async def test_profile_service_flush(mock_memobase_client):
    service = ProfileService(client=mock_memobase_client)
    result = await service.flush("u1")
    assert result["success"] is True
    mock_memobase_client.flush.assert_called_once()


@pytest.mark.asyncio
async def test_profile_service_get_profile(mock_memobase_client):
    service = ProfileService(client=mock_memobase_client)
    result = await service.get_profile("u1")
    assert result["success"] is True
    assert result["data"].user_id == "u1"


@pytest.mark.asyncio
async def test_profile_service_get_context(mock_memobase_client):
    service = ProfileService(client=mock_memobase_client)
    result = await service.get_context("u1")
    assert result["success"] is True
    assert result["data"].user_id == "u1"
