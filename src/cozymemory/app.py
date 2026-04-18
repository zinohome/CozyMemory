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


_DESCRIPTION = """
CozyMemory 是一个**统一 AI 记忆服务平台**，通过单一 API 整合三大记忆引擎：

| 引擎 | 域 | 能力 |
|------|----|------|
| **Mem0** | 对话记忆 | 自动从对话中提取事实，支持语义搜索 |
| **Memobase** | 用户画像 | 结构化存储用户偏好、背景信息，生成 LLM 上下文提示词 |
| **Cognee** | 知识图谱 | 文档添加 → 知识图谱构建 → 图谱检索 |

## 快速上手

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 添加对话记忆
curl -X POST http://localhost:8000/api/v1/conversations \\
  -H "Content-Type: application/json" \\
  -d '{"user_id":"user_01","messages":[{"role":"user","content":"我喜欢打篮球"}]}'

# 语义搜索
curl -X POST http://localhost:8000/api/v1/conversations/search \\
  -H "Content-Type: application/json" \\
  -d '{"user_id":"user_01","query":"用户喜欢什么运动"}'
```

## 错误格式

所有错误统一返回 `ErrorResponse`：

```json
{"success": false, "error": "Mem0Error", "detail": "upstream timeout", "engine": "Mem0"}
```

- `502` — 引擎后端不可用（5xx 或网络超时）
- `400` — 请求参数被引擎拒绝（4xx）
- `404` — 资源不存在
- `422` — 请求体校验失败
"""

_TAGS_METADATA = [
    {
        "name": "health",
        "description": "服务及三大引擎的健康状态检查。",
    },
    {
        "name": "conversations",
        "description": (
            "**对话记忆**（引擎：Mem0）。\n\n"
            "添加对话后，Mem0 自动用 LLM 提取事实性记忆（如「用户喜欢篮球」）并向量化存储，"
            "支持自然语言语义搜索。"
        ),
    },
    {
        "name": "profiles",
        "description": (
            "**用户画像**（引擎：Memobase）。\n\n"
            "三步流程：`insert`（写入缓冲区）→ `flush`（触发 LLM 处理）"
            "→ `profile`/`context`（读取结果）。\n\n"
            "⚠️ `user_id` 必须是 **UUID v4** 格式。"
        ),
    },
    {
        "name": "knowledge",
        "description": (
            "**知识图谱**（引擎：Cognee）。\n\n"
            "两步流程：`add`（上传文档）→ `cognify`（构建知识图谱，异步，需轮询）"
            "→ `search`（检索）。\n\n"
            "注意：`cognify` 完成前搜索会返回空结果。"
        ),
    },
]


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title=settings.APP_NAME,
        description=_DESCRIPTION,
        version=settings.APP_VERSION,
        openapi_tags=_TAGS_METADATA,
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
