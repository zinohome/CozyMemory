"""
CozyMemory API 主应用

FastAPI 应用入口，配置中间件、路由、异常处理等。
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from contextlib import asynccontextmanager
from datetime import datetime
import time

from ..utils.config import settings
from ..utils.logger import setup_logging, get_logger
from .v1.routes import router as v1_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(
        "CozyMemory 启动",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV
    )
    
    setup_logging()
    
    yield
    
    # 关闭时
    logger.info("CozyMemory 关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="统一 AI 记忆服务平台 - 整合 Mem0、Memobase、Cognee 三大记忆引擎",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        logger.info(
            "请求完成",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )
        
        return response
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "未处理异常",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "InternalServerError",
                "message": "服务器内部错误",
                "details": {"error": str(exc)} if settings.DEBUG else None
            }
        )
    
    # 注册路由
    app.include_router(v1_router)
    
    # 根路径
    @app.get("/", tags=["Root"])
    async def root():
        """根路径"""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "description": "统一 AI 记忆服务平台",
            "docs": "/docs",
            "health": "/api/v1/health"
        }
    
    logger.info("FastAPI 应用创建完成")
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
    )
