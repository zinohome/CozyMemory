"""用户画像服务测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cozymemory.models.profile import (
    ProfileContext,
    ProfileTopic,
    UserProfile,
)
from cozymemory.services.profile import ProfileService
from cozymemory.services.user_mapping import UserMappingService


def _make_user_mapping(resolved_uuid: str = "550e8400-e29b-41d4-a716-446655440000"):
    """构造一个直接返回固定 UUID 的 UserMappingService mock。"""
    mapping = MagicMock(spec=UserMappingService)
    mapping.get_or_create_uuid = AsyncMock(return_value=resolved_uuid)
    return mapping


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


@pytest.fixture
def mock_user_mapping():
    return _make_user_mapping()


@pytest.mark.asyncio
async def test_profile_service_insert(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.insert(user_id="u1", messages=[{"role": "user", "content": "你好"}])
    assert result.success is True
    assert result.blob_id == "blob_123"
    # 透明 UUID 转换：Memobase 客户端收到 UUID 而非原始 user_id
    mock_memobase_client.insert.assert_called_once()
    call_kwargs = mock_memobase_client.insert.call_args.kwargs
    assert call_kwargs["user_id"] == "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.asyncio
async def test_profile_service_flush(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.flush("u1")
    assert result.success is True
    mock_memobase_client.flush.assert_called_once()


@pytest.mark.asyncio
async def test_profile_service_get_profile(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.get_profile("u1")
    assert result.success is True
    assert result.data.user_id == "u1"


@pytest.mark.asyncio
async def test_profile_service_get_context(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.get_context("u1")
    assert result.success is True
    assert result.data.user_id == "u1"


@pytest.mark.asyncio
async def test_profile_service_uses_uuid_for_memobase(mock_memobase_client):
    """验证任意 user_id 都被透明转换为 UUID v4 再传给 Memobase"""
    fixed_uuid = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
    user_mapping = _make_user_mapping(resolved_uuid=fixed_uuid)
    service = ProfileService(client=mock_memobase_client, user_mapping=user_mapping)

    await service.get_profile("arbitrary_string_id")

    mock_memobase_client.profile.assert_called_once_with(user_id=fixed_uuid)


@pytest.mark.asyncio
async def test_profile_service_add_item(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.add_profile_item("u1", "interest", "sport", "游泳")
    assert result.success is True
    assert result.data.content == "游泳"


@pytest.mark.asyncio
async def test_profile_service_delete_item(mock_memobase_client, mock_user_mapping):
    service = ProfileService(client=mock_memobase_client, user_mapping=mock_user_mapping)
    result = await service.delete_profile_item("u1", "p1")
    assert result.success is True
