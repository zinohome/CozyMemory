"""API Key 管理 — Dashboard 侧。

路径：/api/v1/dashboard/apps/{app_id}/keys
鉴权：Bearer JWT（Developer 登录）
权限：
  list / get:         任意 role
  create / rotate:    owner / admin
  update (enable/disable/rename): owner / admin
  delete:             owner 唯一
跨组织隔离：App 不属于当前 Org → 404（不泄露 App 存在）
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import get_current_developer, require_role
from ...db import App, AuditLog, Developer, get_session
from ...models.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyInfo,
    ApiKeyListResponse,
    ApiKeyUpdate,
)
from ...services.api_key_store import ApiKeyStore

router = APIRouter(prefix="/dashboard/apps/{app_id}/keys", tags=["dashboard"])


def _to_info(record) -> ApiKeyInfo:
    return ApiKeyInfo(
        id=record.id,
        app_id=record.app_id,
        name=record.name,
        prefix=record.prefix,
        environment=record.environment,
        disabled=record.disabled,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        expires_at=record.expires_at,
    )


async def _assert_app_in_org(
    app_id: UUID, dev: Developer, session: AsyncSession
) -> App:
    """确认 App 属于当前 Developer 的 Org；否则 404。"""
    result = await session.execute(
        select(App).where(App.id == app_id, App.org_id == dev.org_id)
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="app not found")
    return app


def _audit(
    session: AsyncSession,
    dev: Developer,
    action: str,
    *,
    app_id: UUID,
    key_id: UUID | None,
    request: Request,
    meta: dict | None = None,
) -> None:
    try:
        session.add(
            AuditLog(
                actor_type="developer",
                actor_id=str(dev.id),
                action=action,
                target_type="api_key",
                target_id=str(key_id) if key_id else None,
                app_id=app_id,
                meta=meta,
                ip_address=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        )
    except Exception:
        pass


# ────────── list ──────────


@router.get("", response_model=ApiKeyListResponse, summary="列出该 App 的 API Key")
async def list_keys(
    app_id: UUID,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyListResponse:
    await _assert_app_in_org(app_id, dev, session)
    store = ApiKeyStore(session)
    records = await store.list_for_app(app_id)
    return ApiKeyListResponse(
        data=[_to_info(r) for r in records], total=len(records)
    )


# ────────── create ──────────


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 API Key — 明文只此一次返回",
)
async def create_key(
    app_id: UUID,
    body: ApiKeyCreate,
    request: Request,
    dev: Developer = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyCreateResponse:
    await _assert_app_in_org(app_id, dev, session)
    store = ApiKeyStore(session)
    record, plaintext = await store.create(
        app_id=app_id, name=body.name, environment=body.environment
    )
    _audit(
        session,
        dev,
        action="api_key.created",
        app_id=app_id,
        key_id=record.id,
        request=request,
        meta={"name": record.name, "environment": record.environment, "prefix": record.prefix},
    )
    await session.commit()
    await session.refresh(record)
    return ApiKeyCreateResponse(record=_to_info(record), key=plaintext)


# ────────── rotate ──────────


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyCreateResponse,
    summary="轮换 API Key — 旧明文立即失效，新明文此次返回",
)
async def rotate_key(
    app_id: UUID,
    key_id: UUID,
    request: Request,
    dev: Developer = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyCreateResponse:
    await _assert_app_in_org(app_id, dev, session)
    store = ApiKeyStore(session)
    result = await store.rotate(key_id, app_id)
    if result is None:
        raise HTTPException(status_code=404, detail="key not found")
    record, plaintext = result
    _audit(
        session,
        dev,
        action="api_key.rotated",
        app_id=app_id,
        key_id=key_id,
        request=request,
    )
    await session.commit()
    await session.refresh(record)
    return ApiKeyCreateResponse(record=_to_info(record), key=plaintext)


# ────────── update (enable/disable/rename) ──────────


@router.patch(
    "/{key_id}",
    response_model=ApiKeyInfo,
    summary="启用/禁用 + 改名（owner/admin）",
)
async def update_key(
    app_id: UUID,
    key_id: UUID,
    body: ApiKeyUpdate,
    request: Request,
    dev: Developer = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyInfo:
    await _assert_app_in_org(app_id, dev, session)
    store = ApiKeyStore(session)
    record = await store.update(
        key_id, app_id, name=body.name, disabled=body.disabled
    )
    if record is None:
        raise HTTPException(status_code=404, detail="key not found")

    changes = {}
    if body.name is not None:
        changes["name"] = body.name
    if body.disabled is not None:
        changes["disabled"] = body.disabled
    if changes:
        _audit(
            session,
            dev,
            action="api_key.updated",
            app_id=app_id,
            key_id=key_id,
            request=request,
            meta=changes,
        )

    await session.commit()
    await session.refresh(record)
    return _to_info(record)


# ────────── delete ──────────


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 API Key（owner 唯一）",
)
async def delete_key(
    app_id: UUID,
    key_id: UUID,
    request: Request,
    dev: Developer = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _assert_app_in_org(app_id, dev, session)
    store = ApiKeyStore(session)
    # 写 audit 用的 meta 需在 delete 前拿到
    record = await store.get_by_id(key_id, app_id)
    if record is None:
        raise HTTPException(status_code=404, detail="key not found")
    meta = {"name": record.name, "prefix": record.prefix}

    await store.delete(key_id, app_id)
    _audit(
        session,
        dev,
        action="api_key.deleted",
        app_id=app_id,
        key_id=None,  # 即将删
        request=request,
        meta=meta,
    )
    await session.commit()
    return None
