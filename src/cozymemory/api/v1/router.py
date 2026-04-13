"""API v1 路由汇总"""

from fastapi import APIRouter

from .conversation import router as conversation_router
from .health import router as health_router
from .knowledge import router as knowledge_router
from .profile import router as profile_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(conversation_router)
router.include_router(profile_router)
router.include_router(knowledge_router)
