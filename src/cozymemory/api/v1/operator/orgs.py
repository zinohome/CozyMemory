"""Operator orgs —— 跨 org 总览。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....db import get_session
from ....db.models import App, Developer, Organization

router = APIRouter(prefix="/orgs", tags=["operator"])


class OrgRow(BaseModel):
    id: str
    name: str
    slug: str
    created_at: str
    dev_count: int
    app_count: int


class OrgListResponse(BaseModel):
    data: list[OrgRow]
    total: int


@router.get("", response_model=OrgListResponse)
async def list_orgs(session: AsyncSession = Depends(get_session)) -> OrgListResponse:
    """跨 org 列表。counts 用 scalar subquery 避免 GROUP BY 复杂度。"""
    dev_count_sq = (
        select(func.count(Developer.id))
        .where(Developer.org_id == Organization.id)
        .scalar_subquery()
    )
    app_count_sq = (
        select(func.count(App.id))
        .where(App.org_id == Organization.id)
        .scalar_subquery()
    )
    stmt = select(
        Organization.id,
        Organization.name,
        Organization.slug,
        Organization.created_at,
        dev_count_sq.label("dev_count"),
        app_count_sq.label("app_count"),
    ).order_by(Organization.created_at)
    rows = (await session.execute(stmt)).all()
    data = [
        OrgRow(
            id=str(r.id),
            name=r.name,
            slug=r.slug,
            created_at=r.created_at.isoformat(),
            dev_count=r.dev_count,
            app_count=r.app_count,
        )
        for r in rows
    ]
    return OrgListResponse(data=data, total=len(data))
