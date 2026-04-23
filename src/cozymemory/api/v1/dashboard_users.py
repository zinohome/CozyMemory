"""Dashboard Users 路由 — 开发者 UI 查 App 下的 external user 映射。

路径：/api/v1/dashboard/apps/{app_id}/users
鉴权：Bearer JWT（Developer 登录）
跨组织隔离：App 不属于当前 Org → 404（不泄露 App 存在）
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth.deps import get_current_developer
from ...db import App, get_session
from ...db.models import Developer
from ...services.user_resolver import UserResolver
from ..deps import get_redis_client

router = APIRouter(prefix="/dashboard/apps/{app_id}/users", tags=["dashboard"])


class ExtUserItem(BaseModel):
    external_user_id: str
    internal_uuid: str
    created_at: str


class ExtUserListResponse(BaseModel):
    data: list[ExtUserItem]
    total: int


async def _assert_app_owned(session: AsyncSession, app_id: UUID, dev: Developer) -> App:
    row = (
        await session.execute(select(App).where(App.id == app_id))
    ).scalar_one_or_none()
    if row is None or row.org_id != dev.org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="app not found")
    return row


@router.get("", response_model=ExtUserListResponse)
async def list_users(
    app_id: UUID,
    limit: int = 50,
    offset: int = 0,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> ExtUserListResponse:
    await _assert_app_owned(session, app_id, dev)
    resolver = UserResolver(session, get_redis_client())
    items = await resolver.list_for_app(app_id, limit=limit, offset=offset)
    total = await resolver.count_for_app(app_id)
    return ExtUserListResponse(
        data=[
            ExtUserItem(
                external_user_id=u.external_user_id,
                internal_uuid=str(u.internal_uuid),
                created_at=u.created_at.isoformat(),
            )
            for u in items
        ],
        total=total,
    )


@router.delete("/{external_user_id}")
async def delete_user(
    app_id: UUID,
    external_user_id: str,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await _assert_app_owned(session, app_id, dev)
    resolver = UserResolver(session, get_redis_client())
    removed = await resolver.delete(app_id, external_user_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    await session.commit()
    return {"success": True}
