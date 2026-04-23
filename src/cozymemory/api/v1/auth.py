"""Developer 账号 API — 注册 / 登录 / whoami。

所有 /auth/* 路由不需要 X-Cozy-API-Key（由 app.py 中间件豁免），
但 /auth/me 需要 Bearer JWT。
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import create_access_token, get_current_developer, hash_password, verify_password
from ...config import settings
from ...db import Developer, Organization, get_session
from ...models.auth import (
    ChangePasswordRequest,
    DeveloperInfo,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_developer_info(dev: Developer, org: Organization) -> DeveloperInfo:
    return DeveloperInfo(
        id=dev.id,
        email=dev.email,
        name=dev.name,
        role=dev.role,
        org_id=dev.org_id,
        org_name=org.name,
        org_slug=org.slug,
        is_active=dev.is_active,
        last_login_at=dev.last_login_at,
    )


def _issue_token(dev: Developer, org: Organization) -> TokenResponse:
    token = create_access_token(
        developer_id=str(dev.id),
        org_id=str(dev.org_id),
        role=dev.role,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
        developer=_to_developer_info(dev, org),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册 — 同时创建 Organization 和首个 Developer(owner)",
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """自注册流程：一次创建 Org + owner Developer，返回 token。

    约束：
      - email 全局唯一（developers.email UNIQUE）
      - org_slug 全局唯一（organizations.slug UNIQUE）
      - 首个 Developer 自动 role=owner
    """
    # 预检查（给前端友好的错误消息；数据库约束做最终 fallback）
    existing_email = await session.execute(
        select(Developer).where(Developer.email == body.email)
    )
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="email already registered")

    existing_slug = await session.execute(
        select(Organization).where(Organization.slug == body.org_slug)
    )
    if existing_slug.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="org_slug already taken")

    org = Organization(name=body.org_name, slug=body.org_slug)
    session.add(org)
    await session.flush()  # 拿到 org.id

    dev = Developer(
        org_id=org.id,
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name or body.email.split("@")[0],
        role="owner",
        last_login_at=datetime.now(UTC),
    )
    session.add(dev)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        # 并发下 email/slug 撞车兜底
        raise HTTPException(status_code=409, detail="conflict on email or org_slug") from e

    await session.refresh(dev)
    await session.refresh(org)

    return _issue_token(dev, org)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="登录 — 邮箱 + 密码换 JWT",
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """验证邮箱 + 密码，成功返回 JWT。

    失败统一返回 401 invalid credentials（不区分"邮箱不存在" vs "密码错"，
    防枚举）。
    """
    result = await session.execute(select(Developer).where(Developer.email == body.email))
    dev = result.scalar_one_or_none()
    if dev is None or not verify_password(body.password, dev.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if not dev.is_active:
        raise HTTPException(status_code=401, detail="account deactivated")

    dev.last_login_at = datetime.now(UTC)
    await session.flush()

    org_result = await session.execute(select(Organization).where(Organization.id == dev.org_id))
    org = org_result.scalar_one()

    await session.commit()
    return _issue_token(dev, org)


@router.get(
    "/me",
    response_model=DeveloperInfo,
    summary="返回当前 JWT 对应的 Developer 信息",
)
async def me(
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> DeveloperInfo:
    org_result = await session.execute(select(Organization).where(Organization.id == dev.org_id))
    org = org_result.scalar_one()
    return _to_developer_info(dev, org)


@router.patch(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改当前登录 Developer 的密码",
)
async def change_password(
    body: ChangePasswordRequest,
    dev: Developer = Depends(get_current_developer),
    session: AsyncSession = Depends(get_session),
) -> None:
    """验证旧密码后替换 password_hash。

    安全考虑：不区分"旧密码错"和"账号问题"，统一 401；新密码不允许与旧密码相同。
    """
    if not verify_password(body.old_password, dev.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if body.old_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new password must differ from current",
        )
    dev.password_hash = hash_password(body.new_password)
    await session.commit()
