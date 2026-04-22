"""开发者账号认证模块 — JWT + bcrypt。

与 X-Cozy-API-Key 是两套独立机制：
  - /api/v1/auth/*、/api/v1/dashboard/*  → Bearer JWT（本模块）
  - /api/v1/conversations, profiles, knowledge 等业务路由 → X-Cozy-API-Key

两者 互不干扰。Dashboard JWT 让开发者登进去管理他们的 Org / App / Key；
业务 API Key 让外部 app 调用。
"""

from .deps import get_current_developer, require_role
from .jwt import create_access_token, decode_access_token
from .password import hash_password, verify_password

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_developer",
    "require_role",
]
