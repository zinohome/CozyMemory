"""会话记忆 REST API 端点

对应引擎：Mem0
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...api.deps import get_conversation_service
from ...auth import AppContext, get_app_context
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.conversation import (
    ConversationMemory,
    ConversationMemoryCreate,
    ConversationMemoryListResponse,
    ConversationMemorySearch,
)
from ...services.conversation import ConversationService

logger = structlog.get_logger()

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _engine_error_response(exc: EngineError) -> JSONResponse:
    """将 EngineError 转为统一格式的 JSONResponse"""
    status_code = 502 if exc.status_code is None or exc.status_code >= 500 else 400
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            error=f"{exc.engine}Error",
            detail=exc.message,
            engine=exc.engine,
        ).model_dump(),
    )


@router.get(
    "",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="列出用户所有记忆",
)
async def list_conversations(
    user_id: str,
    limit: int = 100,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse | JSONResponse:
    """获取指定用户的全部记忆条目，按创建时间倒序。"""
    try:
        return await service.get_all(user_id=user_id, limit=limit)
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="添加对话并提取记忆",
)
async def add_conversation(
    request: ConversationMemoryCreate,
    service: ConversationService = Depends(get_conversation_service),
    app_ctx: AppContext | None = Depends(get_app_context),
) -> ConversationMemoryListResponse | JSONResponse:
    """添加对话消息，Mem0 自动使用 LLM 提取事实性记忆并向量化存储。

    `infer=true`（默认）：LLM 分析对话提取事实，如"用户喜欢篮球"。
    `infer=false`：原样存储消息内容，不做提取。

    注：batch 17 Phase 2 Step 4 起，如果调用方用的是 App API Key，请求会
    携带 App 上下文（app_id）。目前只做日志记录，不做数据隔离；Step 5
    引入 uuid5 映射后 Step 6 会把 `request.user_id` 转成内部 UUID，
    实现真正的 per-App 隔离。
    """
    if app_ctx:
        logger.info(
            "conversation.add.app_scope",
            app_id=str(app_ctx.app_id),
            api_key_id=str(app_ctx.api_key_id),
            external_user_id=request.user_id,
        )
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.add(
            user_id=request.user_id,
            messages=messages,
            metadata=request.metadata,
            infer=request.infer,
            agent_id=request.agent_id,
            session_id=request.session_id,
        )
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/search",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="语义搜索记忆",
)
async def search_conversations(
    request: ConversationMemorySearch,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse | JSONResponse:
    """用自然语言语义搜索用户记忆。支持 `threshold` 过滤低相关结果。"""
    try:
        return await service.search(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
            agent_id=request.agent_id,
            session_id=request.session_id,
            memory_scope=request.memory_scope,
        )
    except EngineError as e:
        return _engine_error_response(e)


@router.get(
    "/{memory_id}",
    response_model=ConversationMemory,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="获取单条记忆",
)
async def get_conversation(
    memory_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemory | JSONResponse:
    """按 ID 获取单条记忆。记忆不存在返回 404。"""
    try:
        result = await service.get(memory_id)
        if result is None:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    success=False, error="NotFoundError", detail="记忆不存在"
                ).model_dump(),
            )
        return result
    except EngineError as e:
        return _engine_error_response(e)


@router.delete(
    "/{memory_id}",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="删除单条记忆",
)
async def delete_conversation(
    memory_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse | JSONResponse:
    """按 ID 删除单条记忆。"""
    try:
        return await service.delete(memory_id)
    except EngineError as e:
        return _engine_error_response(e)


@router.delete(
    "",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
    summary="删除用户所有记忆",
)
async def delete_all_conversations(
    user_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse | JSONResponse:
    """删除指定用户的全部记忆条目。"""
    try:
        return await service.delete_all(user_id)
    except EngineError as e:
        return _engine_error_response(e)
