"""Operator (bootstrap key only) 路由集合。

这些路由提供全局 ops 视角：跨 org 的 user mapping / 备份 / 全局数据浏览。
中间件已保证 /api/v1/operator/* 只接 bootstrap key，拒 JWT（Step 8.1 / app.py）。
"""
from fastapi import APIRouter

from .backup import router as backup_router
from .users_mapping import router as users_mapping_router

router = APIRouter(prefix="/operator")
router.include_router(users_mapping_router)
router.include_router(backup_router)
