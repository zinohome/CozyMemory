"""API Key 存储服务

Redis 为存储后端：
  cozy:apikey:ids                 set<id>        所有 key 的 ID 集合（便于 list）
  cozy:apikey:hash:<sha256>       str = id       hash → id 反向索引（auth 校验用）
  cozy:apikey:<id>                hash           {name, prefix, key_hash, created_at,
                                                  last_used_at, disabled}

明文 key 只在创建/轮换时短暂出现，随后丢弃；服务端只存 sha256。
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis

from ..models.admin import ApiKeyCreateResponse, ApiKeyRecord

_IDS_KEY = "cozy:apikey:ids"
_HASH_PREFIX = "cozy:apikey:hash:"
_META_PREFIX = "cozy:apikey:"


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _generate_key() -> tuple[str, str]:
    """返回 (plaintext, prefix_for_display)。

    plaintext 形如 cozy_<32 hex>_<48 hex>，总 87 字符，~320 bits 熵。
    显示前缀用 key 的前 14 字符（cozy_ + 8 hex），既可识别又不泄露。
    """
    body = secrets.token_hex(16)  # 32 hex = 128 bits
    tail = secrets.token_hex(24)  # 48 hex = 192 bits
    plaintext = f"cozy_{body}_{tail}"
    prefix = plaintext[:14]  # "cozy_" + 前 9 hex 显示
    return plaintext, prefix


class ApiKeyStore:
    """Redis 后端的 API Key CRUD"""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._r = redis_client

    # ===== 内部辅助 =====

    async def _load_meta(self, key_id: str) -> ApiKeyRecord | None:
        raw = await self._r.hgetall(f"{_META_PREFIX}{key_id}")
        if not raw:
            return None
        data = {k.decode() if isinstance(k, bytes) else k: (v.decode() if isinstance(v, bytes) else v) for k, v in raw.items()}
        try:
            return ApiKeyRecord(
                id=key_id,
                name=data.get("name", ""),
                prefix=data.get("prefix", ""),
                created_at=datetime.fromisoformat(data["created_at"]),
                last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
                disabled=data.get("disabled", "0") == "1",
            )
        except (KeyError, ValueError):
            return None

    async def _save_meta(self, rec: ApiKeyRecord, key_hash: str | None = None) -> None:
        payload = {
            "name": rec.name,
            "prefix": rec.prefix,
            "created_at": rec.created_at.isoformat(),
            "disabled": "1" if rec.disabled else "0",
        }
        if rec.last_used_at:
            payload["last_used_at"] = rec.last_used_at.isoformat()
        if key_hash:
            payload["key_hash"] = key_hash
        await self._r.hset(f"{_META_PREFIX}{rec.id}", mapping=payload)

    # ===== 公开 API =====

    async def list_keys(self) -> list[ApiKeyRecord]:
        ids_raw = await self._r.smembers(_IDS_KEY)
        ids = [i.decode() if isinstance(i, bytes) else i for i in ids_raw]
        records: list[ApiKeyRecord] = []
        for kid in ids:
            rec = await self._load_meta(kid)
            if rec:
                records.append(rec)
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records

    async def create(self, name: str) -> ApiKeyCreateResponse:
        plaintext, prefix = _generate_key()
        key_hash = _hash_key(plaintext)
        key_id = str(uuid.uuid4())
        rec = ApiKeyRecord(
            id=key_id,
            name=name,
            prefix=prefix,
            created_at=datetime.now(timezone.utc),
            last_used_at=None,
            disabled=False,
        )
        await self._save_meta(rec, key_hash=key_hash)
        await self._r.sadd(_IDS_KEY, key_id)
        await self._r.set(f"{_HASH_PREFIX}{key_hash}", key_id)
        return ApiKeyCreateResponse(record=rec, key=plaintext)

    async def rotate(self, key_id: str) -> ApiKeyCreateResponse | None:
        rec = await self._load_meta(key_id)
        if not rec:
            return None
        # 删除旧 hash 索引
        old_hash_raw = await self._r.hget(f"{_META_PREFIX}{key_id}", "key_hash")
        if old_hash_raw:
            old_hash = old_hash_raw.decode() if isinstance(old_hash_raw, bytes) else old_hash_raw
            await self._r.delete(f"{_HASH_PREFIX}{old_hash}")
        # 生成新 key
        plaintext, prefix = _generate_key()
        key_hash = _hash_key(plaintext)
        rec.prefix = prefix
        rec.last_used_at = None
        await self._save_meta(rec, key_hash=key_hash)
        await self._r.set(f"{_HASH_PREFIX}{key_hash}", key_id)
        return ApiKeyCreateResponse(record=rec, key=plaintext)

    async def update(self, key_id: str, name: str | None = None, disabled: bool | None = None) -> ApiKeyRecord | None:
        rec = await self._load_meta(key_id)
        if not rec:
            return None
        if name is not None:
            rec.name = name
        if disabled is not None:
            rec.disabled = disabled
        await self._save_meta(rec)
        return rec

    async def delete(self, key_id: str) -> bool:
        old_hash_raw = await self._r.hget(f"{_META_PREFIX}{key_id}", "key_hash")
        if old_hash_raw:
            old_hash = old_hash_raw.decode() if isinstance(old_hash_raw, bytes) else old_hash_raw
            await self._r.delete(f"{_HASH_PREFIX}{old_hash}")
        deleted = await self._r.delete(f"{_META_PREFIX}{key_id}")
        await self._r.srem(_IDS_KEY, key_id)
        return deleted > 0

    async def verify_and_touch(self, plaintext: str) -> str | None:
        """鉴权入口：若 plaintext 命中未禁用的 key，更新 last_used_at 并返回 id；否则 None"""
        if not plaintext:
            return None
        key_hash = _hash_key(plaintext)
        id_raw = await self._r.get(f"{_HASH_PREFIX}{key_hash}")
        if not id_raw:
            return None
        key_id = id_raw.decode() if isinstance(id_raw, bytes) else id_raw
        # 检查 disabled
        disabled_raw = await self._r.hget(f"{_META_PREFIX}{key_id}", "disabled")
        if disabled_raw and (disabled_raw.decode() if isinstance(disabled_raw, bytes) else disabled_raw) == "1":
            return None
        # 更新 last_used_at
        await self._r.hset(
            f"{_META_PREFIX}{key_id}",
            "last_used_at",
            datetime.now(timezone.utc).isoformat(),
        )
        return key_id
