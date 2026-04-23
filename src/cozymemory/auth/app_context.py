"""App Context 依赖 — 业务路由从 request.state 取 App 归属信息。

中间件 `require_api_key` 在鉴权命中 PG 动态 Key 时已往 request.state 写入：
    request.state.api_key_id
    request.state.app_id

业务路由通过本模块的两种依赖拿到这层信息：

- get_app_context(request)
    宽容版：App Key → 返回 AppContext；bootstrap key 或其他情况 → None
    适合"可选 app 归属"的路由（比如 admin 视角的统计查询）

- require_app_context(request)
    严格版：必须有 App Context；bootstrap / 无 → 403
    适合必须 app 隔离的业务路由（conversations/profiles/knowledge）

AppContext.get_app() 懒加载 App 记录（需要 App.namespace_id 做 uuid5 映射时用）。
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import App, get_session


@dataclass
class AppContext:
    """当前请求的 App 归属 + 鉴权来源。"""

    app_id: UUID
    api_key_id: UUID
    _session: AsyncSession
    _app: App | None = None  # 懒加载缓存

    async def get_app(self) -> App:
        """按需加载 App 记录（含 namespace_id，做 uuid5 映射必需）。
        第一次调用时查 DB；后续调用直接返缓存。"""
        if self._app is None:
            result = await self._session.execute(select(App).where(App.id == self.app_id))
            app = result.scalar_one_or_none()
            if app is None:
                # 理论上不应发生（API Key 指向的 App 应始终存在），防御性处理
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="app context references missing app",
                )
            self._app = app
        return self._app

    async def resolve_user(self, external_user_id: str) -> UUID:
        """便利方法：external_user_id → internal UUID v5。

        调用方（业务路由）拿到这个 UUID 后直接传给 Mem0/Memobase/Cognee。
        底层 UserResolver 负责 uuid5 计算 + PG 索引 upsert + Redis 缓存。
        """
        # 局部 import 避开 cozymemory.auth ↔ services 循环引用
        from ..api.deps import get_redis_client
        from ..services.user_resolver import UserResolver

        app = await self.get_app()
        resolver = UserResolver(self._session, get_redis_client())
        return await resolver.resolve(app, external_user_id)


def get_app_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AppContext | None:
    """宽容版：没有 app 归属时返 None（bootstrap key 走这条路）。"""
    api_key_id = getattr(request.state, "api_key_id", None)
    app_id = getattr(request.state, "app_id", None)
    if not api_key_id or not app_id:
        return None
    try:
        return AppContext(
            app_id=UUID(str(app_id)),
            api_key_id=UUID(str(api_key_id)),
            _session=session,
        )
    except (ValueError, TypeError):
        return None


def require_app_context(
    ctx: AppContext | None = Depends(get_app_context),
) -> AppContext:
    """严格版：必须通过 App Key 访问，bootstrap 或无 → 403。

    业务路由用这个依赖后就能假定请求一定属于某个 App。
    """
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this endpoint requires an App API key (not a bootstrap key)",
        )
    return ctx


async def scope_user_id(app_ctx: AppContext | None, user_id: str) -> str:
    """业务路由通用 helper，把 external_user_id 按鉴权来源做范围化：

    - 有 app_ctx（调用方用 App Key）→ uuid5 解析为内部 UUID 字符串
      传给三引擎（Mem0/Memobase/Cognee）时作为 user_id，实现 per-App 数据隔离
    - 无 app_ctx（bootstrap key，admin 视角）→ 直接返原始 user_id
      保留 "admin 看所有数据" 的既有行为，向后兼容 UI / 迁移期调用

    所有业务路由（conversations / profiles / context / backup）从
    batch 17 Phase 2 Step 6 起统一走这个函数，行为一致。
    """
    if app_ctx is None:
        return user_id
    internal_uuid = await app_ctx.resolve_user(user_id)
    return str(internal_uuid)
