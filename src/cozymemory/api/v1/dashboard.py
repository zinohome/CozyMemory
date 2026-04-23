"""Dashboard API — 开发者管理自己 Org 下的 App。

路径前缀：/api/v1/dashboard
鉴权：全部要 Bearer JWT（Developer 登录）
权限：
  list / get:  任意 role
  create:      owner / admin
  update:      owner / admin
  delete:      owner 唯一
数据隔离：每个请求只能访问自己 org_id 下的 App；否则 404（不泄露 App 存在）。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func

from ...auth import get_current_developer, require_role
from ...db import App, AuditLog, Developer, Organization, get_session
from ...models.app import AppCreate, AppInfo, AppListResponse, AppUpdate
from ...models.auth import (
    MemberInfo,
    MemberListResponse,
    OrganizationInfo,
    UpdateOrganizationRequest,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _to_info(app: App) -> AppInfo:
    return AppInfo(
        id=app.id,
        org_id=app.org_id,
        name=app.name,
        slug=app.slug,
        namespace_id=app.namespace_id,
        description=app.description,
        created_at=app.created_at,
    )


async def _get_own_app(app_id: UUID, dev: Developer, session: AsyncSession) -> App:
    """拿一个 App；如果不属于当前开发者的 Org，返 404 而不是 403
    （防枚举，遵循 GitHub/Stripe 的 "resource not found to you" 语义）。"""
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
    app_id: UUID | None,
    request: Request | None = None,
    meta: dict | None = None,
) -> None:
    """写一条审计日志。失败静默（审计不能阻塞业务）。"""
    try:
        log = AuditLog(
            actor_type="developer",
            actor_id=str(dev.id),
            action=action,
            target_type="app",
            target_id=str(app_id) if app_id else None,
            app_id=app_id,
            meta=meta,
            ip_address=(request.client.host if request and request.client else None),
            user_agent=(request.headers.get("user-agent") if request else None),
        )
        session.add(log)
    except Exception:
        pass


# ───────────────────────── 路由 ─────────────────────────


@router.get(
    "/apps",
    response_model=AppListResponse,
    summary="列出当前开发者 Org 下的所有 App",
)
async def list_apps(
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> AppListResponse:
    result = await session.execute(
        select(App).where(App.org_id == dev.org_id).order_by(App.created_at.desc())
    )
    apps = list(result.scalars().all())
    return AppListResponse(data=[_to_info(a) for a in apps], total=len(apps))


@router.post(
    "/apps",
    response_model=AppInfo,
    status_code=status.HTTP_201_CREATED,
    summary="创建 App（owner/admin）",
)
async def create_app(
    body: AppCreate,
    request: Request,
    dev: Developer = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_session),
) -> AppInfo:
    app = App(
        org_id=dev.org_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        # namespace_id 默认 uuid4，永不变；用于 external_user_id → internal_uuid 的 uuid5 计算
    )
    session.add(app)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail="app slug already exists in this org") from e

    _audit(
        session,
        dev,
        action="app.created",
        app_id=app.id,
        request=request,
        meta={"name": app.name, "slug": app.slug},
    )
    await session.commit()
    await session.refresh(app)
    return _to_info(app)


@router.get(
    "/apps/{app_id}",
    response_model=AppInfo,
    summary="获取 App 详情",
)
async def get_app(
    app_id: UUID,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> AppInfo:
    app = await _get_own_app(app_id, dev, session)
    return _to_info(app)


@router.patch(
    "/apps/{app_id}",
    response_model=AppInfo,
    summary="修改 App 的 name / description（owner/admin）",
)
async def update_app(
    app_id: UUID,
    body: AppUpdate,
    request: Request,
    dev: Developer = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_session),
) -> AppInfo:
    app = await _get_own_app(app_id, dev, session)

    changed: dict[str, str] = {}
    if body.name is not None and body.name != app.name:
        changed["name"] = app.name  # old
        app.name = body.name
    if body.description is not None and body.description != app.description:
        # description 可能很长，只记长度变化
        changed["description_len_delta"] = str(
            len(body.description) - len(app.description)
        )
        app.description = body.description

    if changed:
        _audit(session, dev, action="app.updated", app_id=app.id, request=request, meta=changed)

    await session.commit()
    await session.refresh(app)
    return _to_info(app)


@router.delete(
    "/apps/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除 App 及其全部 API Key / ExternalUser（owner 唯一）",
)
async def delete_app(
    app_id: UUID,
    request: Request,
    dev: Developer = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_session),
) -> None:
    app = await _get_own_app(app_id, dev, session)
    # 先写审计（在 delete 之前，避免 FK 级联后 app_id 失效）
    _audit(
        session,
        dev,
        action="app.deleted",
        app_id=None,  # 将要被删，不引用
        request=request,
        meta={"app_id": str(app.id), "name": app.name, "slug": app.slug},
    )
    await session.delete(app)
    await session.commit()
    # 204 不返 body
    return None


# ── Organization (当前登录者所在 org) ─────────────────────────────────

async def _get_own_org(dev: Developer, session: AsyncSession) -> Organization:
    org = (
        await session.execute(select(Organization).where(Organization.id == dev.org_id))
    ).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="org not found")
    return org


async def _org_counts(org_id: UUID, session: AsyncSession) -> tuple[int, int]:
    dev_count = int(
        (
            await session.execute(
                select(func.count(Developer.id)).where(Developer.org_id == org_id)
            )
        ).scalar()
        or 0
    )
    app_count = int(
        (
            await session.execute(
                select(func.count(App.id)).where(App.org_id == org_id)
            )
        ).scalar()
        or 0
    )
    return dev_count, app_count


@router.get(
    "/organization",
    response_model=OrganizationInfo,
    summary="查看当前 org 信息 + 成员 / App 计数",
)
async def get_organization(
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> OrganizationInfo:
    org = await _get_own_org(dev, session)
    dev_count, app_count = await _org_counts(org.id, session)
    return OrganizationInfo(
        id=org.id,
        name=org.name,
        slug=org.slug,
        created_at=org.created_at,
        developer_count=dev_count,
        app_count=app_count,
    )


@router.patch(
    "/organization",
    response_model=OrganizationInfo,
    summary="修改当前 org 的 name / slug（仅 owner）",
)
async def update_organization(
    body: UpdateOrganizationRequest,
    request: Request,
    dev: Developer = Depends(require_role("owner")),
    session: AsyncSession = Depends(get_session),
) -> OrganizationInfo:
    if body.name is None and body.slug is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="no fields to update"
        )
    org = await _get_own_org(dev, session)
    if body.name is not None:
        org.name = body.name
    if body.slug is not None:
        org.slug = body.slug
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="org_slug already taken"
        )
    _audit(
        session,
        dev,
        action="org.updated",
        app_id=None,
        request=request,
        meta={"changed": {k: v for k, v in body.model_dump().items() if v is not None}},
    )
    await session.commit()
    await session.refresh(org)
    dev_count, app_count = await _org_counts(org.id, session)
    return OrganizationInfo(
        id=org.id,
        name=org.name,
        slug=org.slug,
        created_at=org.created_at,
        developer_count=dev_count,
        app_count=app_count,
    )


@router.get(
    "/organization/developers",
    response_model=MemberListResponse,
    summary="列当前 org 下所有 Developer",
)
async def list_developers(
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> MemberListResponse:
    rows = (
        await session.execute(
            select(Developer)
            .where(Developer.org_id == dev.org_id)
            .order_by(Developer.created_at)
        )
    ).scalars().all()
    return MemberListResponse(
        data=[
            MemberInfo(
                id=d.id,
                email=d.email,
                name=d.name,
                role=d.role,
                is_active=d.is_active,
                last_login_at=d.last_login_at,
                created_at=d.created_at,
            )
            for d in rows
        ],
        total=len(rows),
    )
