"""JWT 编码 / 解码 — HS256，24h TTL。

Payload 结构：
  sub     (developer UUID 字符串)
  org_id  (organization UUID)
  role    ('owner' / 'admin' / 'member')
  exp     (过期时间戳，Unix s)
  iat     (签发时间戳，Unix s)

错误处理：decode_access_token 对所有 jwt 异常统一抛 ValueError，
上层转成 401。
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from ..config import settings


def create_access_token(
    developer_id: str,
    org_id: str,
    role: str,
    ttl_seconds: int | None = None,
) -> str:
    """签发 JWT。ttl_seconds 不传则用 settings 默认（24h）。"""
    now = datetime.now(UTC)
    payload = {
        "sub": developer_id,
        "org_id": org_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(seconds=ttl_seconds or settings.JWT_ACCESS_TOKEN_TTL_SECONDS)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """解 JWT；失败（签名错 / 过期 / 格式错）统一抛 ValueError。"""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as e:
        raise ValueError("token expired") from e
    except jwt.InvalidTokenError as e:
        raise ValueError("invalid token") from e
