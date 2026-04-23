"""Knowledge 路由 per-App scope helpers。

Bootstrap key → 这些函数直接返回或 no-op（app_ctx=None）。
App Key / Bearer+AppId → 登记 / 校验 / 过滤。
"""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import AppContext
from ...services.dataset_registry import AppDatasetRegistry


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


async def register_dataset_for_app(
    app_ctx: AppContext | None,
    dataset_id: str,
    session: AsyncSession,
) -> None:
    """bootstrap → no-op。App → 登记（幂等）。"""
    if app_ctx is None:
        return
    u = _parse_uuid(dataset_id)
    if u is None:
        return
    await AppDatasetRegistry(session).register(app_ctx.app_id, u)
    await session.commit()


async def ensure_owned(
    app_ctx: AppContext | None,
    dataset_id: str,
    session: AsyncSession,
) -> None:
    """bootstrap → no-op。App → 校验归属，跨 App / legacy 均 404（防枚举）。"""
    if app_ctx is None:
        return
    u = _parse_uuid(dataset_id)
    if u is None or not await AppDatasetRegistry(session).is_owned_by(app_ctx.app_id, u):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset not found")


async def unregister_dataset(
    app_ctx: AppContext | None,
    dataset_id: str,
    session: AsyncSession,
) -> None:
    if app_ctx is None:
        return
    u = _parse_uuid(dataset_id)
    if u is None:
        return
    await AppDatasetRegistry(session).unregister(u)
    await session.commit()


async def filter_datasets_for_app(
    app_ctx: AppContext | None,
    datasets: list,  # list of KnowledgeDataset with .id
    session: AsyncSession,
) -> list:
    if app_ctx is None:
        return datasets
    owned = await AppDatasetRegistry(session).list_for_app(app_ctx.app_id)
    return [d for d in datasets if _parse_uuid(d.id) in owned]


async def resolve_name_to_id(service, name: str) -> str | None:
    """通过 list_datasets 查名字对应的 id。未找到返 None。"""
    try:
        resp = await service.list_datasets()
    except Exception:
        return None
    for d in resp.data or []:
        if d.name == name:
            return d.id
    return None
