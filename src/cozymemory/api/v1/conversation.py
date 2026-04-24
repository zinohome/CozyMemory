"""会话记忆 REST API 端点

对应引擎：Mem0

batch 17 Phase 2 Step 6 起：所有涉及 user_id 的路由走 scope_user_id，
App Key 调用 → 解成 internal UUID；bootstrap key → 保留原 user_id 透传。
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select

from ...api.deps import get_conversation_service
from ...auth import AppContext, get_app_context, scope_user_id
from ...clients.base import EngineError
from ...db.models import ExternalUser
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


async def _user_belongs_to_app(app_ctx: AppContext, mem0_user_id: str) -> bool:
    """检查 Mem0 memory 的 user_id（internal uuid）是否属于当前 App。"""
    from uuid import UUID as _UUID

    try:
        uid = _UUID(mem0_user_id)
    except (ValueError, TypeError):
        return False
    session = app_ctx._session
    result = await session.execute(
        select(ExternalUser.internal_uuid).where(
            ExternalUser.app_id == app_ctx.app_id,
            ExternalUser.internal_uuid == uid,
        )
    )
    return result.scalar_one_or_none() is not None


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
    app_ctx: AppContext | None = Depends(get_app_context),
) -> ConversationMemoryListResponse | JSONResponse:
    """获取指定用户的全部记忆条目，按创建时间倒序。"""
    scoped_uid = await scope_user_id(app_ctx, user_id)
    try:
        return await service.get_all(user_id=scoped_uid, limit=limit)
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
    """
    scoped_uid = await scope_user_id(app_ctx, request.user_id)
    if app_ctx:
        logger.info(
            "conversation.add.app_scope",
            app_id=str(app_ctx.app_id),
            external_user_id=request.user_id,
            internal_uuid=scoped_uid,
        )
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.add(
            user_id=scoped_uid,
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
    app_ctx: AppContext | None = Depends(get_app_context),
) -> ConversationMemoryListResponse | JSONResponse:
    """用自然语言语义搜索用户记忆。支持 `threshold` 过滤低相关结果。"""
    scoped_uid = await scope_user_id(app_ctx, request.user_id)
    try:
        return await service.search(
            user_id=scoped_uid,
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
    app_ctx: AppContext | None = Depends(get_app_context),
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
        if app_ctx and not await _user_belongs_to_app(app_ctx, result.user_id):
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
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
    summary="删除单条记忆",
)
async def delete_conversation(
    memory_id: str,
    service: ConversationService = Depends(get_conversation_service),
    app_ctx: AppContext | None = Depends(get_app_context),
) -> ConversationMemoryListResponse | JSONResponse:
    """按 ID 删除单条记忆。"""
    try:
        if app_ctx:
            existing = await service.get(memory_id)
            if existing is None or not await _user_belongs_to_app(app_ctx, existing.user_id):
                return JSONResponse(
                    status_code=404,
                    content=ErrorResponse(
                        success=False, error="NotFoundError", detail="记忆不存在"
                    ).model_dump(),
                )
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
    app_ctx: AppContext | None = Depends(get_app_context),
) -> ConversationMemoryListResponse | JSONResponse:
    """删除指定用户的全部记忆条目。"""
    scoped_uid = await scope_user_id(app_ctx, user_id)
    try:
        return await service.delete_all(scoped_uid)
    except EngineError as e:
        return _engine_error_response(e)
