"""gRPC 请求级上下文 —— 拦截器把鉴权结果塞进来，servicer 方法读取。

用 contextvars 保证每个 gRPC call 独立状态；不污染其他 task。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass
class GrpcRequestState:
    app_id: UUID | None = None  # None = bootstrap key（admin 透传）
    api_key_id: UUID | None = None


_request_state: ContextVar[GrpcRequestState | None] = ContextVar(
    "cozymemory_grpc_request_state", default=None
)


def set_state(state: GrpcRequestState) -> None:
    _request_state.set(state)


def clear_state() -> None:
    _request_state.set(None)


def get_state() -> GrpcRequestState | None:
    return _request_state.get()


def get_app_id() -> UUID | None:
    s = _request_state.get()
    return s.app_id if s is not None else None


async def scope_user_id_grpc(external_user_id: str) -> str:
    """与 REST scope_user_id 同义：

    - bootstrap key（state 为 None 或 app_id 为 None）→ 原样返回
    - App Key → uuid5(app.namespace_id, external_user_id)
    """
    s = get_state()
    if s is None or s.app_id is None:
        return external_user_id
    # 局部 import 避免循环
    from sqlalchemy import select

    from ..api.deps import get_redis_client
    from ..db import engine as _db_engine
    from ..db.models import App
    from ..services.user_resolver import UserResolver

    if _db_engine._session_factory is None:
        _db_engine.init_engine()
    assert _db_engine._session_factory is not None
    async with _db_engine._session_factory() as session:
        app = (
            await session.execute(select(App).where(App.id == s.app_id))
        ).scalar_one_or_none()
        if app is None:
            return external_user_id
        resolver = UserResolver(session, get_redis_client())
        internal = await resolver.resolve(app, external_user_id)
        await session.commit()
        return str(internal)
