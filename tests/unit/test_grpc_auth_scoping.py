"""gRPC 鉴权 + per-App scoping + usage (Step 8.17)。

覆盖：
- 无 metadata → UNAUTHENTICATED
- 无效 metadata → UNAUTHENTICATED
- bootstrap metadata → RPC 业务继续（不因鉴权被拒）
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from cozymemory.db.models import Base
from cozymemory.grpc_server import (
    conversation_pb2,
    conversation_pb2_grpc,
)
from cozymemory.models.conversation import (
    ConversationMemory,
    ConversationMemoryListResponse,
)

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cozymemory_user:cozymemory_pass@localhost:5433/cozymemory_test",
)
BOOTSTRAP_KEY = "bootstrap-grpc-test"

pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true" or os.getenv("GITHUB_ACTIONS") == "true",
    reason="requires local postgres",
)


@pytest.fixture(autouse=True)
async def _prep_db_and_settings():
    """建表 + 清表；设置 bootstrap key + test DB URL。"""
    from cozymemory.config import settings as _s
    from cozymemory.db import engine as db_engine

    _s.COZY_API_KEYS = BOOTSTRAP_KEY
    _s.DATABASE_URL = DATABASE_URL
    # 强制下次 init_engine 重建
    db_engine._engine = None
    db_engine._session_factory = None

    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for t in reversed(Base.metadata.sorted_tables):
            await conn.execute(t.delete())
    await engine.dispose()
    yield


@pytest.fixture
def mock_conv_service():
    """Patch ConversationService 以避免真实 Mem0 后端。"""
    svc = MagicMock()
    svc.add = AsyncMock(
        return_value=ConversationMemoryListResponse(
            success=True,
            data=[ConversationMemory(id="m1", user_id="u1", content="hi")],
            total=1,
            message="ok",
        )
    )
    return svc


@pytest.fixture
async def grpc_server_running(mock_conv_service):
    """启一台带 AuthUsageInterceptor 的 gRPC server 到随机端口。"""
    from grpc import aio

    from cozymemory.grpc_server import conversation_pb2_grpc as _convgrpc
    from cozymemory.grpc_server.auth_interceptor import AuthUsageInterceptor
    from cozymemory.grpc_server.server import ConversationGrpcServicer

    servicer = ConversationGrpcServicer()
    servicer._svc = mock_conv_service  # 注入 mock

    server = aio.server(interceptors=[AuthUsageInterceptor()])
    _convgrpc.add_ConversationServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        yield f"127.0.0.1:{port}"
    finally:
        await server.stop(grace=0)


@pytest.mark.asyncio
async def test_grpc_no_auth_rejected(grpc_server_running):
    """没带 x-cozy-api-key metadata → UNAUTHENTICATED。"""
    async with grpc.aio.insecure_channel(grpc_server_running) as ch:
        stub = conversation_pb2_grpc.ConversationServiceStub(ch)
        with pytest.raises(grpc.RpcError) as exc_info:
            await stub.AddConversation(
                conversation_pb2.AddConversationRequest(
                    user_id="x",
                    messages=[conversation_pb2.Message(role="user", content="hi")],
                ),
            )
        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
async def test_grpc_invalid_key_rejected(grpc_server_running):
    """x-cozy-api-key 无效 → UNAUTHENTICATED。"""
    async with grpc.aio.insecure_channel(grpc_server_running) as ch:
        stub = conversation_pb2_grpc.ConversationServiceStub(ch)
        with pytest.raises(grpc.RpcError) as exc_info:
            await stub.AddConversation(
                conversation_pb2.AddConversationRequest(
                    user_id="x",
                    messages=[conversation_pb2.Message(role="user", content="hi")],
                ),
                metadata=(("x-cozy-api-key", "totally-bogus-key"),),
            )
        assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


@pytest.mark.asyncio
async def test_grpc_bootstrap_passes(grpc_server_running, mock_conv_service):
    """带 bootstrap key → 业务 handler 被调到。"""
    async with grpc.aio.insecure_channel(grpc_server_running) as ch:
        stub = conversation_pb2_grpc.ConversationServiceStub(ch)
        resp = await stub.AddConversation(
            conversation_pb2.AddConversationRequest(
                user_id="x",
                messages=[conversation_pb2.Message(role="user", content="hi")],
            ),
            metadata=(("x-cozy-api-key", BOOTSTRAP_KEY),),
        )
        assert resp.success is True
        mock_conv_service.add.assert_awaited_once()
        # bootstrap → passthrough：external user_id 原样传下去
        kwargs = mock_conv_service.add.await_args.kwargs
        assert kwargs["user_id"] == "x"
