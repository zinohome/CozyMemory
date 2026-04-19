"""UserMappingService 单元测试"""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from cozymemory.services.user_mapping import UserMappingService


def _make_redis(get_return=None, set_return=True):
    """构造模拟 Redis 客户端

    Args:
        get_return: redis.get 返回值（None 或 bytes/str）
        set_return: redis.set（SET NX）返回值；True=NX 抢占成功，None/False=已存在
    """
    redis = MagicMock()
    redis.get = AsyncMock(return_value=get_return)
    redis.set = AsyncMock(return_value=set_return)
    redis.setex = AsyncMock(return_value=True)
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
        """快路径：Redis 已有映射（bytes），直接返回，不调用 SET"""
        existing = b"550e8400-e29b-41d4-a716-446655440000"
        redis = _make_redis(get_return=existing)
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.get_or_create_uuid("user_01")

        assert result == "550e8400-e29b-41d4-a716-446655440000"
        redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_existing_uuid_str(self):
        """快路径：Redis 已有映射（str），直接返回"""
        existing = "550e8400-e29b-41d4-a716-446655440000"
        redis = _make_redis(get_return=existing)
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.get_or_create_uuid("user_01")

        assert result == "550e8400-e29b-41d4-a716-446655440000"
        redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_uuid_when_missing(self):
        """慢路径：SET NX 成功 → 写入反向键 → 返回新 UUID"""
        redis = _make_redis(get_return=None, set_return=True)
        svc = UserMappingService(redis=redis, ttl=0)

        with patch("cozymemory.services.user_mapping.uuid.uuid4") as mock_uuid:
            mock_uuid.return_value = uuid.UUID("aaaabbbb-cccc-dddd-eeee-ffffffffffff")
            result = await svc.get_or_create_uuid("new_user")

        assert result == "aaaabbbb-cccc-dddd-eeee-ffffffffffff"
        # SET NX 写正向键（TTL=0，使用 set(nx=True)）
        fwd_call = call("cm:uid:new_user", "aaaabbbb-cccc-dddd-eeee-ffffffffffff", nx=True)
        assert fwd_call in redis.set.call_args_list
        # 反向键也用 set（TTL=0 时），共 2 次调用
        assert redis.set.await_count == 2
        redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_set_when_ttl_zero(self):
        """TTL=0：正向键使用 set(..., nx=True)，反向键使用 set"""
        redis = _make_redis(get_return=None, set_return=True)
        svc = UserMappingService(redis=redis, ttl=0)

        await svc.get_or_create_uuid("u1")

        # SET NX 用于正向键
        assert redis.set.call_count >= 2  # 正向(NX) + 反向
        redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_setex_when_ttl_set(self):
        """TTL>0：正向键使用 set(..., ex=ttl, nx=True)，反向键使用 setex"""
        redis = _make_redis(get_return=None, set_return=True)
        svc = UserMappingService(redis=redis, ttl=3600)

        await svc.get_or_create_uuid("u1")

        # 正向键：set(..., ex=3600, nx=True)
        set_calls = redis.set.call_args_list
        assert any(c.kwargs.get("ex") == 3600 and c.kwargs.get("nx") is True for c in set_calls)
        # 反向键：setex
        redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_race_condition_nx_fails_returns_winner_uuid(self):
        """SET NX 失败（另一请求抢先）→ 读取赢家 UUID 返回"""
        winner_uuid = b"winner-uuid-str"
        redis = MagicMock()
        # 第一次 GET：None（尚未存在）；第二次 GET：赢家写入的值
        redis.get = AsyncMock(side_effect=[None, winner_uuid])
        redis.set = AsyncMock(return_value=None)  # NX 失败
        svc = UserMappingService(redis=redis, ttl=0)

        result = await svc.get_or_create_uuid("contested_user")

        assert result == "winner-uuid-str"
        # SET NX 被尝试过一次
        redis.set.assert_awaited_once()


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
