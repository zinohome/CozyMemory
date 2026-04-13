"""用户画像 REST API 端点

对应引擎：Memobase
"""

from fastapi import APIRouter, Depends, HTTPException

from ...api.deps import get_profile_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.profile import (
    ProfileContextRequest,
    ProfileFlushRequest,
    ProfileInsertRequest,
    ProfileInsertResponse,
)
from ...services.profile import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post(
    "/insert", response_model=ProfileInsertResponse, responses={502: {"model": ErrorResponse}}
)
async def insert_profile(
    request: ProfileInsertRequest, service: ProfileService = Depends(get_profile_service)
):
    """插入对话到 Memobase 缓冲区，自动提取画像"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.insert(user_id=request.user_id, messages=messages, sync=request.sync)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.post("/flush", responses={502: {"model": ErrorResponse}})
async def flush_profile(
    request: ProfileFlushRequest, service: ProfileService = Depends(get_profile_service)
):
    """触发缓冲区处理"""
    try:
        return await service.flush(user_id=request.user_id, sync=request.sync)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.get("/{user_id}", responses={502: {"model": ErrorResponse}})
async def get_profile(user_id: str, service: ProfileService = Depends(get_profile_service)):
    """获取用户结构化画像"""
    try:
        return await service.get_profile(user_id)
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )


@router.post("/{user_id}/context", responses={502: {"model": ErrorResponse}})
async def get_context(
    user_id: str,
    request: ProfileContextRequest,
    service: ProfileService = Depends(get_profile_service),
):
    """获取上下文提示词"""
    try:
        chats = None
        if request.chats:
            chats = [{"role": m.role, "content": m.content} for m in request.chats]
        return await service.get_context(
            user_id=user_id, max_token_size=request.max_token_size, chats=chats
        )
    except EngineError as e:
        raise HTTPException(
            status_code=502 if e.status_code and e.status_code >= 500 else 400,
            detail=f"Memobase 引擎错误: {e.message}",
        )
