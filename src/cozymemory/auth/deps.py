"""FastAPI 依赖 — 解 Bearer JWT 拿当前 Developer。

用法：
    from cozymemory.auth import get_current_developer

    @router.get("/me")
    async def me(dev: Developer = Depends(get_current_developer)):
        return dev
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Developer, get_session
from .jwt import decode_access_token

# auto_error=False: 没带 Authorization header 时不抛 403，交给我们自己返 401
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_developer(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> Developer:
    """解 Bearer token，加载 Developer 返回。

    401 场景：
      - 没带 Authorization header
      - 格式不是 Bearer
      - token 签名错 / 过期
      - token 合法但 Developer 不存在（被删了）
      - Developer.is_active == False
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(creds.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    try:
        dev_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="malformed token",
        ) from e

    result = await session.execute(select(Developer).where(Developer.id == dev_id))
    developer = result.scalar_one_or_none()
    if developer is None or not developer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="developer not found or deactivated",
        )
    return developer


def require_role(*allowed: str):
    """依赖工厂：限制路由只有指定 role 能访问。

    用法：
        @router.delete("/apps/{id}", dependencies=[Depends(require_role("owner", "admin"))])
    """

    async def _check(dev: Developer = Depends(get_current_developer)) -> Developer:
        if dev.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires one of roles: {', '.join(allowed)}",
            )
        return dev

    return _check
