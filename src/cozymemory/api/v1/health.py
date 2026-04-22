"""健康检查端点"""

import time

import structlog
from fastapi import APIRouter

from ...api.deps import get_cognee_client, get_mem0_client, get_memobase_client
from ...config import settings
from ...metrics import engine_latency_ms, engine_up
from ...models.common import EngineStatus, HealthResponse

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
async def health_check() -> HealthResponse:
    """检查服务及三大引擎（Mem0、Memobase、Cognee）的健康状态。

    返回整体状态（`healthy` / `degraded` / `unhealthy`）及每个引擎的响应延迟。
    部分引擎不可用时整体状态为 `degraded`，不影响其他引擎正常使用。
    """
    engines: dict[str, EngineStatus] = {}

    # 检查 Mem0
    if settings.MEM0_ENABLED:
        try:
            mem0_client = get_mem0_client()
            start = time.time()
            healthy = await mem0_client.health_check()
            latency = (time.time() - start) * 1000
            engines["mem0"] = EngineStatus(
                name="Mem0",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error=str(e))
    else:
        engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error="disabled")

    # 检查 Memobase
    if settings.MEMOBASE_ENABLED:
        try:
            memobase_client = get_memobase_client()
            start = time.time()
            healthy = await memobase_client.health_check()
            latency = (time.time() - start) * 1000
            engines["memobase"] = EngineStatus(
                name="Memobase",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error=str(e))
    else:
        engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error="disabled")

    # 检查 Cognee
    if settings.COGNEE_ENABLED:
        try:
            cognee_client = get_cognee_client()
            start = time.time()
            healthy = await cognee_client.health_check()
            latency = (time.time() - start) * 1000
            engines["cognee"] = EngineStatus(
                name="Cognee",
                status="healthy" if healthy else "unhealthy",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            engines["cognee"] = EngineStatus(name="Cognee", status="unhealthy", error=str(e))
    else:
        engines["cognee"] = EngineStatus(name="Cognee", status="unhealthy", error="disabled")

    # 计算整体状态
    healthy_count = sum(1 for e in engines.values() if e.status == "healthy")
    total_count = len(engines)

    if healthy_count == total_count:
        overall = "healthy"
    elif healthy_count > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    # 写 Prometheus 指标：每次 /health 调用都更新
    # （Prom scrape 时会拉到最新值；UI/外部监控共用）
    for key, engine in engines.items():
        engine_up.labels(engine=key).set(1 if engine.status == "healthy" else 0)
        if engine.latency_ms is not None:
            engine_latency_ms.labels(engine=key).set(engine.latency_ms)

    return HealthResponse(status=overall, engines=engines)
