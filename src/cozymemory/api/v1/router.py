"""API v1 路由汇总"""

from fastapi import APIRouter

from .api_keys import router as api_keys_router
from .auth import router as auth_router
from .context import router as context_router
from .conversation import router as conversation_router
from .dashboard import router as dashboard_router
from .dashboard_users import router as dashboard_users_router
from .health import router as health_router
from .knowledge import router as knowledge_router
from .operator import router as operator_router
from .profile import router as profile_router

router = APIRouter(prefix="/api/v1")
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(dashboard_router)  # /dashboard/apps
router.include_router(api_keys_router)  # /dashboard/apps/{app_id}/keys
router.include_router(dashboard_users_router)  # /dashboard/apps/{app_id}/users
router.include_router(conversation_router)
router.include_router(profile_router)
router.include_router(knowledge_router)
router.include_router(context_router)
router.include_router(operator_router)  # /operator/users-mapping, /operator/backup
