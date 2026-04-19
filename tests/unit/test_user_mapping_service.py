"""UserMappingService 单元测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cozymemory.services.user_mapping import UserMappingService


def _make_redis(get_return=None):
    """构造模拟 Redis 客户端"""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=get_return)
    pipeline = MagicMock()
    pipeline.set = MagicMock()
    pipeline.setex = MagicMock()
    pipeline.delete = MagicMock()
    pipeline.execute = AsyncMock(return_value=[True, True])
    redis.pipeline = MagicMock(return_value=pipeline)
    return redis


class TestGetOrCreateUuid:

    @pytest.mark.asyncio
    async def test_returns_existing_uuid_bytes(self):
        existing = b"550e8400-e29b-41d4-a716-446655440000"
        redis = _make_redis(get_return=existing)
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.get_or_create_uuid("user_01")
        assert result == "550e8400-e29b-41d4-a716-446655440000"
        redis.pipeline.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_existing_uuid_str(self):
        existing = "550e8400-e29b-41d4-a716-446655440000"
        redis = _make_redis(get_return=existing)
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.get_or_create_uuid("user_01")
        assert result == "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_creates_new_uuid_when_missing(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=0)

        with patch("cozymemory.services.user_mapping.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("aaaabbbb-cccc-dddd-eeee-ffffffffffff")
            result = await svc.get_or_create_uuid("new_user")

        assert result == "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        pipeline = redis.pipeline.return_value
        pipeline.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uses_set_when_ttl_zero(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=0)

        await svc.get_or_create_uuid("u1")

        pipeline = redis.pipeline.return_value
        assert pipeline.set.call_count == 2
        pipeline.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_setex_when_ttl_set(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=3600)

        await svc.get_or_create_uuid("u1")

        pipeline = redis.pipeline.return_value
        assert pipeline.setex.call_count == 2
        pipeline.set.assert_not_called()


class TestGetUuid:

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=0)
        assert await svc.get_uuid("unknown") is None

    @pytest.mark.asyncio
    async def test_returns_uuid_string(self):
        redis = _make_redis(get_return=b"abc-123")
        svc = UserMappingService(redis=redis, ttl=0)
        assert await svc.get_uuid("u1") == "abc-123"


class TestGetUserId:

    @pytest.mark.asyncio
    async def test_returns_none_when_missing(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=0)
        assert await svc.get_user_id("some-uuid") is None

    @pytest.mark.asyncio
    async def test_returns_user_id(self):
        redis = _make_redis(get_return=b"user_01")
        svc = UserMappingService(redis=redis, ttl=0)
        assert await svc.get_user_id("some-uuid") == "user_01"


class TestDeleteMapping:

    @pytest.mark.asyncio
    async def test_returns_false_when_no_mapping(self):
        redis = _make_redis(get_return=None)
        svc = UserMappingService(redis=redis, ttl=0)
        result = await svc.delete_mapping("unknown_user")
        assert result is False

    @pytest.mark.asyncio
    async def test_deletes_both_keys_and_returns_true(self):
        redis = _make_redis(get_return=b"some-uuid-str")
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.delete_mapping("user_01")

        assert result is True
        pipeline = redis.pipeline.return_value
        assert pipeline.delete.call_count == 2
        pipeline.execute.assert_awaited_once()
