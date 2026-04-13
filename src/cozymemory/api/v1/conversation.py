"""会话记忆 REST API 端点

对应引擎：Mem0
"""

from fastapi import APIRouter, Depends, HTTPException

from ...api.deps import get_conversation_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.conversation import (
    ConversationMemory,
    ConversationMemoryCreate,
    ConversationMemoryListResponse,
    ConversationMemorySearch,
)
from ...services.conversation import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post(
    "", response_model=ConversationMemoryListResponse, responses={502: {"model": ErrorResponse}}
)
async def add_conversation(
    request: ConversationMemoryCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse:
    """添加对话，Mem0 自动提取事实性记忆"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.add(
            user_id=request.user_id,
            messages=messages,
            metadata=request.metadata,
            infer=request.infer,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.post(
    "/search",
    response_model=ConversationMemoryListResponse,
    responses={502: {"model": ErrorResponse}},
)
async def search_conversations(
    request: ConversationMemorySearch,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationMemoryListResponse:
    """搜索会话记忆"""
    try:
        return await service.search(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.get(
    "/{memory_id}", response_model=ConversationMemory, responses={404: {"model": ErrorResponse}}
)
async def get_conversation(
    memory_id: str, service: ConversationService = Depends(get_conversation_service)
) -> ConversationMemory:
    """获取单条记忆"""
    try:
        result = await service.get(memory_id)
        if result is None:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return result
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.delete("/{memory_id}", response_model=ConversationMemoryListResponse)
async def delete_conversation(
    memory_id: str, service: ConversationService = Depends(get_conversation_service)
) -> ConversationMemoryListResponse:
    """删除单条记忆"""
    try:
        return await service.delete(memory_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )


@router.delete("", response_model=ConversationMemoryListResponse)
async def delete_all_conversations(
    user_id: str, service: ConversationService = Depends(get_conversation_service)
) -> ConversationMemoryListResponse:
    """删除用户所有记忆"""
    try:
        return await service.delete_all(user_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Mem0 引擎错误: {e.message}",
        )
