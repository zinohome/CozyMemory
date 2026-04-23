"""App ↔ Cognee Dataset 归属注册表。

作用：
- create_dataset / add 创建新 dataset 时，把 (app_id, dataset_id) 登记
- list_datasets 按当前 app_id 过滤
- 对 dataset_id 做 CRUD 前校验归属，防 cross-App 枚举

调用方：business routes 里的 knowledge 路由。bootstrap key 访问不走这里
（Operator 视角看全局）。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AppDataset


class AppDatasetRegistry:
    """记录 (app_id, dataset_id) 映射；一个 dataset 恰属一个 app。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(self, app_id: UUID, dataset_id: UUID) -> None:
        """登记归属。幂等（重复 register 同对不报错）。"""
        stmt = (
            pg_insert(AppDataset)
            .values(app_id=app_id, dataset_id=dataset_id)
            .on_conflict_do_nothing(index_elements=["dataset_id"])
        )
        await self.session.execute(stmt)

    async def is_owned_by(self, app_id: UUID, dataset_id: UUID) -> bool:
        row = (
            await self.session.execute(
                select(AppDataset).where(
                    AppDataset.dataset_id == dataset_id,
                    AppDataset.app_id == app_id,
                )
            )
        ).scalar_one_or_none()
        return row is not None

    async def list_for_app(self, app_id: UUID) -> set[UUID]:
        rows = (
            await self.session.execute(
                select(AppDataset.dataset_id).where(AppDataset.app_id == app_id)
            )
        ).all()
        return {r[0] for r in rows}

    async def unregister(self, dataset_id: UUID) -> None:
        """删除 dataset 时调用，解除归属。dataset_id PK 唯一，直接删即可。"""
        row = (
            await self.session.execute(
                select(AppDataset).where(AppDataset.dataset_id == dataset_id)
            )
        ).scalar_one_or_none()
        if row is not None:
            await self.session.delete(row)
