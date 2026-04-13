"""健康检查端点"""

import time
import logging

from fastapi import APIRouter

from ...config import settings
from ...models.common import EngineStatus, HealthResponse
from ...api.deps import get_mem0_client, get_memobase_client, get_cognee_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """检查服务及所有引擎的健康状态"""
    engines: dict[str, EngineStatus] = {}

    # 检查 Mem0
    if settings.MEM0_ENABLED:
        try:
            client = get_mem0_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["mem0"] = EngineStatus(
                name="Mem0", status="healthy" if healthy else "unhealthy", latency_ms=round(latency, 1)
            )
        except Exception as e:
            engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error=str(e))
    else:
        engines["mem0"] = EngineStatus(name="Mem0", status="unhealthy", error="disabled")

    # 检查 Memobase
    if settings.MEMOBASE_ENABLED:
        try:
            client = get_memobase_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["memobase"] = EngineStatus(
                name="Memobase", status="healthy" if healthy else "unhealthy", latency_ms=round(latency, 1)
            )
        except Exception as e:
            engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error=str(e))
    else:
        engines["memobase"] = EngineStatus(name="Memobase", status="unhealthy", error="disabled")

    # 检查 Cognee
    if settings.COGNEE_ENABLED:
        try:
            client = get_cognee_client()
            start = time.time()
            healthy = await client.health_check()
            latency = (time.time() - start) * 1000
            engines["cognee"] = EngineStatus(
                name="Cognee", status="healthy" if healthy else "unhealthy", latency_ms=round(latency, 1)
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

    return HealthResponse(status=overall, engines=engines)