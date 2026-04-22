"""Auth 模块单元测试 — password / JWT 两部分。

不依赖 PG / 网络，纯函数级。/auth API 端到端放 integration tests。
"""

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from cozymemory.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from cozymemory.config import settings

# ───────────────────────── Password ─────────────────────────


def test_hash_password_produces_bcrypt():
    h = hash_password("secret123")
    # bcrypt hash 格式: $2a$ / $2b$ / $2y$，总长 60
    assert h.startswith("$2")
    assert len(h) == 60


def test_hash_is_salted():
    """同一个明文两次 hash 结果不同（盐随机）"""
    assert hash_password("same") != hash_password("same")


def test_verify_success():
    h = hash_password("password123")
    assert verify_password("password123", h) is True


def test_verify_wrong_password():
    h = hash_password("password123")
    assert verify_password("wrong", h) is False


def test_verify_corrupt_hash_is_false():
    """损坏的 hash 不应抛异常，返回 False。"""
    assert verify_password("x", "not-a-real-hash") is False


def test_verify_empty_password():
    h = hash_password("real")
    assert verify_password("", h) is False


def test_bcrypt_72_byte_limit_silent_truncation():
    """bcrypt 只用前 72 字节；passlib 静默截断。记录这个行为。"""
    long_pwd = "a" * 100
    h = hash_password(long_pwd)
    # 只取前 72 字节比较，应该仍然 verify 通过
    assert verify_password("a" * 72, h) is True
    assert verify_password("a" * 100, h) is True  # 后 28 字节被忽略


# ───────────────────────── JWT ─────────────────────────


def test_create_and_decode_roundtrip():
    token = create_access_token(
        developer_id="11111111-1111-1111-1111-111111111111",
        org_id="22222222-2222-2222-2222-222222222222",
        role="owner",
    )
    decoded = decode_access_token(token)
    assert decoded["sub"] == "11111111-1111-1111-1111-111111111111"
    assert decoded["org_id"] == "22222222-2222-2222-2222-222222222222"
    assert decoded["role"] == "owner"
    assert "exp" in decoded
    assert "iat" in decoded


def test_token_ttl_default_24h():
    token = create_access_token("d1", "o1", "owner")
    decoded = decode_access_token(token)
    # 过期时间约 24h 后（允许 ±10s 的 timing 抖动）
    now = datetime.now(UTC).timestamp()
    expected = now + settings.JWT_ACCESS_TOKEN_TTL_SECONDS
    assert abs(decoded["exp"] - expected) < 10


def test_custom_ttl():
    token = create_access_token("d", "o", "member", ttl_seconds=60)
    decoded = decode_access_token(token)
    now = datetime.now(UTC).timestamp()
    assert abs(decoded["exp"] - (now + 60)) < 5


def test_expired_token_raises_value_error():
    """手工构造一个过期的 token"""
    payload = {
        "sub": "x",
        "org_id": "o",
        "role": "owner",
        "iat": int((datetime.now(UTC) - timedelta(hours=48)).timestamp()),
        "exp": int((datetime.now(UTC) - timedelta(hours=24)).timestamp()),  # 过期 24h
    }
    expired = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(expired)


def test_invalid_signature_raises():
    token = create_access_token("d", "o", "owner")
    # 掐掉最后一个字符破坏签名
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError, match="invalid"):
        decode_access_token(bad)


def test_garbage_string_raises():
    with pytest.raises(ValueError, match="invalid"):
        decode_access_token("not-a-jwt-at-all")
