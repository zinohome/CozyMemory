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
