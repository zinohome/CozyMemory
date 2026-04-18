"""CozyMemory FastAPI 应用入口"""

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .api.v1.router import router as v1_router
from .config import settings
from .logging_config import configure_logging
from .models.common import ErrorResponse

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    configure_logging(env=settings.APP_ENV, level=settings.LOG_LEVEL)
    logger.info(
        "cozymemory.startup",
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        debug=settings.DEBUG,
    )
    yield
    logger.info("cozymemory.shutdown")


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
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求日志中间件：绑定 request_id / method / path 到 structlog contextvars
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Response:
        request_id = str(uuid.uuid4())[:8]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "http.request",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    # 全局未捕获异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("http.unhandled_exception", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error="InternalServerError",
                detail=str(exc) if settings.DEBUG else "Internal server error",
            ).model_dump(),
        )

    # 注册路由
    app.include_router(v1_router)

    return app
