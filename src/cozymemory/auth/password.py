"""密码哈希 — 直接用 bcrypt 库（避开 passlib 与 bcrypt 4.x 的兼容 bug）。

bcrypt 的 72 字节限制在这里显式处理：超长明文截断到前 72 字节。
密码复杂度不由本模块校验，由 API 层 Pydantic 约束。
"""

import bcrypt

_MAX_BYTES = 72


def _truncate_to_bcrypt_limit(plaintext: str) -> bytes:
    """bcrypt 只处理前 72 字节；超过部分静默丢弃（与 passlib 行为一致）。"""
    encoded = plaintext.encode("utf-8")
    return encoded[:_MAX_BYTES]


def hash_password(plaintext: str) -> str:
    """生成 bcrypt hash，60 字符字符串（含算法头 + 盐 + hash）。"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(_truncate_to_bcrypt_limit(plaintext), salt)
    return hashed.decode("utf-8")


def verify_password(plaintext: str, hashed: str) -> bool:
    """验证明文和 hash 匹配；hash 损坏时返回 False 而不是抛。"""
    try:
        return bcrypt.checkpw(
            _truncate_to_bcrypt_limit(plaintext),
            hashed.encode("utf-8"),
        )
    except Exception:
        return False
