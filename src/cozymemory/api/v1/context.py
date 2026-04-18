"""统一上下文 REST API 端点"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...api.deps import get_context_service
from ...models.context import ContextRequest, ContextResponse
from ...services.context import ContextService

router = APIRouter(prefix="/context", tags=["context"])


@router.post(
    "",
    response_model=ContextResponse,
    summary="并发获取三类记忆（统一上下文）",
)
async def get_unified_context(
    request: ContextRequest,
    service: ContextService = Depends(get_context_service),
) -> ContextResponse:
    """一次请求并发调用 Mem0、Memobase、Cognee，返回合并后的统一上下文。

    **适用场景**：LLM 调用前的上下文准备阶段，用单次往返替代三次串行请求。

    **延迟特性**：总延迟 = max(各引擎延迟)，而非各引擎延迟之和。

    **容错特性**：某个引擎失败时，其他引擎结果正常返回，
    失败原因记录在响应的 `errors` 字段中。

    **query 行为**：
    - 有值 → Mem0 语义搜索 + Cognee 知识图谱检索
    - 为 null → Mem0 返回全量记忆（按时间倒序），Cognee 自动跳过
    """
    return await service.get_context(request)
