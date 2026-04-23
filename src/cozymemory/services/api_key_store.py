"""API Key 存储 - PG 版（取代原 Redis ApiKeyStore）。

设计要点：
  - Key 明文只在 create/rotate 返回一次，服务端只存 sha256
  - 查询 + verify 走 PG；last_used_at 也写 PG（后续可加 Redis 缓存优化）
  - Key 归属到 App（外键 app_id），和 Org/Developer 权限挂钩
  - bootstrap key（env COZY_API_KEYS）不走 PG，继续在中间件里前置校验

Key 格式：cozy_live_<32 hex>_<48 hex>  或  cozy_test_...
         前缀用于 UI 展示，也能从前缀推断环境。
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ApiKey


def hash_key(plaintext: str) -> str:
    """sha256 hex 64 字符。"""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def generate_key(environment: str = "live") -> tuple[str, str]:
    """生成明文 key + 展示用 prefix。

    格式: cozy_<env>_<16 hex>_<24 hex>  约 60 字符，~320 bit 熵
    prefix: 前 18 字符 = cozy_<env>_<前 8 hex>
    """
    body = secrets.token_hex(16)  # 32 hex
    tail = secrets.token_hex(24)  # 48 hex
    plaintext = f"cozy_{environment}_{body}_{tail}"
    prefix = plaintext[:18]  # "cozy_live_" + 8 hex 前缀
    return plaintext, prefix


class ApiKeyStore:
    """PG 版 API Key 管理。每次实例化绑一个 AsyncSession。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ────────── list ──────────

    async def list_for_app(self, app_id: UUID) -> list[ApiKey]:
        """列出某 App 下全部 key，按 created_at 倒序。"""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.app_id == app_id).order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, key_id: UUID, app_id: UUID) -> ApiKey | None:
        """拿指定 key，限定到 app（防跨组织访问）。"""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.app_id == app_id)
        )
        return result.scalar_one_or_none()

    # ────────── create / rotate ──────────

    async def create(
        self, *, app_id: UUID, name: str, environment: str = "live"
    ) -> tuple[ApiKey, str]:
        """创建一把 key。返回 (record, plaintext)；明文只此一次返回。"""
        plaintext, prefix = generate_key(environment)
        record = ApiKey(
            app_id=app_id,
            name=name,
            key_hash=hash_key(plaintext),
            prefix=prefix,
            environment=environment,
            disabled=False,
        )
        self.session.add(record)
        await self.session.flush()
        return record, plaintext

    async def rotate(self, key_id: UUID, app_id: UUID) -> tuple[ApiKey, str] | None:
        """用新明文替换旧明文，保留 id/name/环境。旧明文立即失效。"""
        record = await self.get_by_id(key_id, app_id)
        if record is None:
            return None
        new_plain, new_prefix = generate_key(record.environment)
        record.key_hash = hash_key(new_plain)
        record.prefix = new_prefix
        record.last_used_at = None  # 轮换后重置使用时间
        await self.session.flush()
        return record, new_plain

    # ────────── update ──────────

    async def update(
        self,
        key_id: UUID,
        app_id: UUID,
        *,
        name: str | None = None,
        disabled: bool | None = None,
    ) -> ApiKey | None:
        record = await self.get_by_id(key_id, app_id)
        if record is None:
            return None
        if name is not None:
            record.name = name
        if disabled is not None:
            record.disabled = disabled
        await self.session.flush()
        return record

    # ────────── delete ──────────

    async def delete(self, key_id: UUID, app_id: UUID) -> bool:
        record = await self.get_by_id(key_id, app_id)
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.flush()
        return True

    # ────────── verify (auth 热路径) ──────────

    async def verify_and_touch(self, plaintext: str) -> ApiKey | None:
        """鉴权主入口：plaintext → 如果命中活跃 key 则返回 record，否则 None。

        命中会顺带 UPDATE last_used_at。
        """
        if not plaintext:
            return None
        h = hash_key(plaintext)
        result = await self.session.execute(select(ApiKey).where(ApiKey.key_hash == h))
        record = result.scalar_one_or_none()
        if record is None or record.disabled:
            return None
        # 过期检查（expires_at NULL = 不过期）
        if record.expires_at is not None and record.expires_at < datetime.now(UTC):
            return None
        # 更新 last_used_at（可选，写放大的话后续可迁 Redis）
        record.last_used_at = datetime.now(UTC)
        try:
            await self.session.flush()
        except IntegrityError:
            # 并发更新冲突时，不阻塞主请求
            await self.session.rollback()
        return record
