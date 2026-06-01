"""幂等创建 CozyMemory 平台管理员账号（Developer + Organization）。

部署 entrypoint 自动调用，确保管理员账号始终存在。
凭据从环境变量读取：
  SEED_ADMIN_EMAIL    (default: admin@cozy.dev)
  SEED_ADMIN_PASSWORD (default: Admin1234!)
  SEED_ADMIN_ORG_NAME (default: Cozy Admin)
  SEED_ADMIN_ORG_SLUG (default: cozy-admin)

用法：python -m scripts.seed_admin_developer
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

SEED_ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "admin@cozy.dev")
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "Admin1234!")
SEED_ADMIN_ORG_NAME = os.environ.get("SEED_ADMIN_ORG_NAME", "Cozy Admin")
SEED_ADMIN_ORG_SLUG = os.environ.get("SEED_ADMIN_ORG_SLUG", "cozy-admin")
DATABASE_URL = os.environ.get("DATABASE_URL", "")


async def main() -> int:
    if not DATABASE_URL:
        print("[seed_admin_developer] DATABASE_URL not set, skipping seed")
        return 0

    from cozymemory.auth.password import hash_password
    from cozymemory.db.models import Developer, Organization

    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        result = await session.execute(
            select(Developer).where(Developer.email == SEED_ADMIN_EMAIL)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            print(
                f"[seed_admin_developer] Developer {SEED_ADMIN_EMAIL} already exists, skipping"
            )
            await engine.dispose()
            return 0

        slug_result = await session.execute(
            select(Organization).where(Organization.slug == SEED_ADMIN_ORG_SLUG)
        )
        existing_org = slug_result.scalar_one_or_none()

        if existing_org is None:
            org = Organization(name=SEED_ADMIN_ORG_NAME, slug=SEED_ADMIN_ORG_SLUG)
            session.add(org)
            await session.flush()
        else:
            org = existing_org

        dev = Developer(
            org_id=org.id,
            email=SEED_ADMIN_EMAIL,
            password_hash=hash_password(SEED_ADMIN_PASSWORD),
            name="Admin",
            role="owner",
            last_login_at=datetime.now(UTC),
        )
        session.add(dev)
        await session.commit()
        print(
            f"[seed_admin_developer] Created Developer {SEED_ADMIN_EMAIL} (org={SEED_ADMIN_ORG_SLUG})"
        )

    await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
