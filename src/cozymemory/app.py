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

from .api.deps import close_all_clients
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
    await close_all_clients()
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
    {
        "name": "context",
        "description": (
            "**统一上下文**（跨三大引擎）。\n\n"
            "单次请求并发调用 Mem0、Memobase、Cognee，"
            "总延迟 = max(各引擎延迟)。\n\n"
            "适用于 LLM 调用前的上下文准备阶段，"
            "部分引擎失败时其余引擎结果仍正常返回。"
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

    # API Key 鉴权中间件。鉴权源（两者任一命中即通过）：
    #   a. COZY_API_KEYS 环境变量里的 bootstrap key（不可删除，admin 权限）
    #   b. Redis 里用户创建的动态 key（可 CRUD，普通权限）
    # 鉴权关闭的条件：env 为空 AND 不想强制（通过 COZY_AUTH_REQUIRE_DYNAMIC
    # 开关暂不支持）。当 env 空 = 关闭。
    _AUTH_EXEMPT_PREFIXES = (
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/metrics",
        "/api/v1/auth",  # 开发者注册/登录走 JWT，不走 X-Cozy-API-Key
        "/api/v1/dashboard",  # Dashboard 管理接口走 JWT，不走 X-Cozy-API-Key
    )

    # Step 8: 业务路由白名单 —— Bearer 分支无 AppId 调这些路径 → 401。
    # 管理类路径（dashboard / auth）由 _AUTH_EXEMPT_PREFIXES 豁免，不进中间件。
    _BEARER_REQUIRES_APP_ID_PREFIXES = (
        "/api/v1/conversations",
        "/api/v1/profiles",
        "/api/v1/context",
        "/api/v1/knowledge",
    )

    @app.middleware("http")
    async def require_api_key(request: Request, call_next: Any) -> Response:
        if not settings.auth_enabled:
            return await call_next(request)
        path = request.url.path
        if path == "/" or any(path.startswith(p) for p in _AUTH_EXEMPT_PREFIXES):
            return await call_next(request)
        if request.method == "OPTIONS":  # CORS 预检直接放行
            return await call_next(request)

        provided = request.headers.get("x-cozy-api-key", "")
        authorization = request.headers.get("authorization", "")

        ok = False
        # 1) X-Cozy-API-Key — 外部 App 路径（优先）
        if provided and provided in settings.api_keys_set:
            ok = True
        elif provided:
            try:
                from .db.engine import _session_factory, init_engine
                from .services.api_key_store import ApiKeyStore

                if _session_factory is None:
                    init_engine()
                assert _session_factory is not None
                async with _session_factory() as s:
                    store = ApiKeyStore(s)
                    record = await store.verify_and_touch(provided)
                    await s.commit()
                    if record is not None:
                        ok = True
                        request.state.api_key_id = str(record.id)
                        request.state.app_id = str(record.app_id)
            except Exception:
                ok = False
        # 2) Bearer JWT + 可选 X-Cozy-App-Id — Dashboard UI 路径
        elif authorization.startswith("Bearer "):
            path = request.url.path
            # Step 8: /operator/* 拒 JWT —— 那里只认 bootstrap
            if path.startswith("/api/v1/operator"):
                ok = False
            else:
                try:
                    from sqlalchemy import select as _select

                    from .auth.jwt import decode_access_token
                    from .db.engine import _session_factory, init_engine
                    from .db.models import App, Developer
                    if _session_factory is None:
                        init_engine()
                    assert _session_factory is not None
                    payload = decode_access_token(authorization[7:])
                    dev_id = payload.get("sub")
                    async with _session_factory() as s:
                        dev = (await s.execute(
                            _select(Developer).where(Developer.id == dev_id)
                        )).scalar_one_or_none()
                        if dev is None:
                            ok = False
                        else:
                            app_id_hdr = request.headers.get("x-cozy-app-id", "")
                            if app_id_hdr:
                                row = (await s.execute(
                                    _select(App).where(App.id == app_id_hdr)
                                )).scalar_one_or_none()
                                if row is None or str(row.org_id) != str(dev.org_id):
                                    ok = False
                                else:
                                    ok = True
                                    request.state.app_id = str(row.id)
                                    request.state.api_key_id = None
                                    request.state.developer_id = str(dev.id)
                            else:
                                # Step 8: 业务路由强制 AppId；其他路径（非业务）放行
                                if any(path.startswith(p) for p in _BEARER_REQUIRES_APP_ID_PREFIXES):
                                    ok = False
                                else:
                                    ok = True
                                    request.state.developer_id = str(dev.id)
                except Exception:
                    ok = False

        if not ok:
            origin = request.headers.get("origin")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ErrorResponse(
                    success=False,
                    error="Unauthorized",
                    detail="Missing or invalid X-Cozy-API-Key / Bearer token; business routes require X-Cozy-App-Id when using Bearer",
                ).model_dump(),
                headers={
                    "Access-Control-Allow-Origin": origin or "*",
                    "Vary": "Origin",
                },
            )

        return await call_next(request)

    # Step 8.16: per-App API 用量记录。仅业务路由；bootstrap key 或无 app_id
    # 场景直接 passthrough。失败永远不阻塞业务响应。
    _USAGE_TRACKED_PREFIXES = (
        "/api/v1/conversations",
        "/api/v1/profiles",
        "/api/v1/context",
        "/api/v1/knowledge",
    )

    def _normalize_route(path: str) -> str:
        p = path.removeprefix("/api/v1/")
        parts = p.split("/", 2)
        if not parts[0]:
            return "unknown"
        base = parts[0]
        if len(parts) == 1:
            return base
        rest = parts[1]
        if rest in (
            "search",
            "datasets",
            "add",
            "add-files",
            "cognify",
            "insert",
            "flush",
        ):
            return f"{base}.{rest}"
        return f"{base}.item"

    @app.middleware("http")
    async def record_api_usage(request: Request, call_next: Any) -> Response:
        path = request.url.path
        tracked = any(path.startswith(p) for p in _USAGE_TRACKED_PREFIXES)
        if not tracked:
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        try:
            app_id_raw = getattr(request.state, "app_id", None)
            if not app_id_raw:
                return response  # bootstrap key or no scope → skip
            from uuid import UUID as _UUID

            from .db import engine as _db_engine
            from .db.models import APIUsage

            if _db_engine._session_factory is None:
                _db_engine.init_engine()
            session_factory = _db_engine._session_factory
            assert session_factory is not None
            duration_ms = (time.perf_counter() - start) * 1000
            from .metrics import app_request_total

            app_request_total.labels(
                app_id=str(app_id_raw),
                route=_normalize_route(path),
                method=request.method,
                status=str(response.status_code),
            ).inc()
            async with session_factory() as s:
                s.add(
                    APIUsage(
                        app_id=_UUID(str(app_id_raw)),
                        route=_normalize_route(path),
                        method=request.method,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                    )
                )
                await s.commit()
        except Exception:
            pass  # usage logging 永远不能阻塞业务响应
        return response

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

    # Prometheus 指标暴露 — /metrics endpoint 给 Prom scrape
    # 默认指标包含：http_requests_total、http_request_duration_seconds、
    #              http_request_size_bytes、http_response_size_bytes，按 handler/method/status 分组。
    # /health 和 /metrics 本身排除（避免自引用和高频干扰）。
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/api/v1/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # 自定义引擎健康 gauge — 每次 /api/v1/health 被调用时更新
    # 由 HealthResponse 路由侧写入
    return app
