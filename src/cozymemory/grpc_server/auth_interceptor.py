"""gRPC 服务端拦截器：鉴权 + 用量记录。

鉴权来源（和 REST 中间件对齐）：
- x-cozy-api-key metadata = bootstrap → 放行（state.app_id=None，admin 透传）
- x-cozy-api-key metadata = 动态 App Key → 验证后写 app_id / api_key_id
- 缺少或无效 → UNAUTHENTICATED

用量：RPC 完成后若 app_id 存在，写一行 APIUsage（route = 'Svc.Method'，method='GRPC'）。
"""

from __future__ import annotations

import time
from typing import Any, Callable
from uuid import UUID

import grpc
import structlog
from grpc import aio

from ..config import settings
from .app_ctx import GrpcRequestState, clear_state, set_state

logger = structlog.get_logger()


def _method_to_route(method: str) -> str:
    """/package.Svc/Method → 'Svc.Method'，截掉 package。"""
    parts = method.strip("/").split("/")
    if len(parts) != 2:
        return method.strip("/")
    svc = parts[0].rsplit(".", 1)[-1]  # 去掉 package
    return f"{svc}.{parts[1]}"


async def _verify_api_key(provided: str) -> tuple[bool, UUID | None, UUID | None]:
    """返回 (ok, app_id, api_key_id)。

    - bootstrap 命中：(True, None, None)
    - 动态 App Key 命中：(True, app_id, api_key_id)
    - 无效 / 空：(False, None, None)
    """
    if not provided:
        return False, None, None
    if provided in settings.api_keys_set:
        return True, None, None
    try:
        from ..db import engine as _db_engine
        from ..services.api_key_store import ApiKeyStore

        if _db_engine._session_factory is None:
            _db_engine.init_engine()
        assert _db_engine._session_factory is not None
        async with _db_engine._session_factory() as s:
            record = await ApiKeyStore(s).verify_and_touch(provided)
            await s.commit()
            if record is not None:
                return True, record.app_id, record.id
    except Exception as exc:  # pragma: no cover - 降级路径
        logger.warning("grpc.auth.verify_error", error=str(exc))
    return False, None, None


async def _record_usage(
    app_id: UUID, route: str, status_code: int, duration_ms: float
) -> None:
    """异步写一行 APIUsage。失败不影响主流程。"""
    try:
        from ..db import engine as _db_engine
        from ..db.models import APIUsage

        if _db_engine._session_factory is None:
            _db_engine.init_engine()
        assert _db_engine._session_factory is not None
        async with _db_engine._session_factory() as s:
            s.add(
                APIUsage(
                    app_id=app_id,
                    route=route,
                    method="GRPC",
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            )
            await s.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning("grpc.usage.record_error", error=str(exc))


class AuthUsageInterceptor(aio.ServerInterceptor):
    """单一拦截器完成鉴权 + usage 落盘。

    注意：只处理 unary_unary（Phase 2 所有 RPC 都是 unary）。
    """

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        handler = await continuation(handler_call_details)
        if handler is None:
            return None

        method_name = handler_call_details.method
        route = _method_to_route(method_name)

        md = {
            k.lower(): v
            for k, v in (handler_call_details.invocation_metadata or [])
        }
        provided = md.get("x-cozy-api-key", "")

        # 只处理 unary_unary（本项目所有 RPC）
        if handler.unary_unary is None:
            return handler

        original_behavior = handler.unary_unary

        async def new_behavior(request: Any, context: grpc.aio.ServicerContext) -> Any:
            start = time.perf_counter()
            ok, app_id, api_key_id = await _verify_api_key(provided)

            if not ok:
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "Missing or invalid x-cozy-api-key metadata",
                )
                return None  # pragma: no cover

            set_state(GrpcRequestState(app_id=app_id, api_key_id=api_key_id))
            status_int = 200
            try:
                return await original_behavior(request, context)
            except Exception:
                status_int = 500
                raise
            finally:
                if app_id is not None:
                    duration_ms = (time.perf_counter() - start) * 1000
                    # 如果 context 记了 gRPC 状态码，转成类 HTTP 表示
                    try:
                        code = context.code()
                        if code is not None and code != grpc.StatusCode.OK:
                            status_int = 500 if status_int == 200 else status_int
                    except Exception:
                        pass
                    await _record_usage(app_id, route, status_int, duration_ms)
                clear_state()

        return grpc.unary_unary_rpc_method_handler(
            new_behavior,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
