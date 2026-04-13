"""CozyMemory FastAPI 应用入口"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.v1.router import router as v1_router
from .config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"CozyMemory starting v{settings.APP_VERSION} env={settings.APP_ENV}")
    yield
    logger.info("CozyMemory shutting down")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        description="统一 AI 记忆服务平台 - 整合 Mem0、Memobase、Cognee 三大引擎",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000
        logger.info(f"{request.method} {request.url.path} {response.status_code} {duration:.1f}ms")
        return response

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "InternalServerError",
                "detail": str(exc) if settings.DEBUG else "服务器内部错误",
            },
        )

    # 注册路由
    app.include_router(v1_router)

    return app
