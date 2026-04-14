"""用户画像 REST API 端点

对应引擎：Memobase
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...api.deps import get_profile_service
from ...clients.base import EngineError
from ...models.common import ErrorResponse
from ...models.profile import (
    ProfileContextRequest,
    ProfileContextResponse,
    ProfileFlushRequest,
    ProfileFlushResponse,
    ProfileGetResponse,
    ProfileInsertRequest,
    ProfileInsertResponse,
)
from ...services.profile import ProfileService

router = APIRouter(prefix="/profiles", tags=["profiles"])


def _engine_error_response(exc: EngineError) -> JSONResponse:
    """将 EngineError 转为统一格式的 JSONResponse"""
    status_code = 502 if exc.status_code and exc.status_code >= 500 else 400
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            success=False,
            error=f"{exc.engine}Error",
            detail=exc.message,
            engine=exc.engine,
        ).model_dump(),
    )


@router.post(
    "/insert", response_model=ProfileInsertResponse, responses={502: {"model": ErrorResponse}}
)
async def insert_profile(
    request: ProfileInsertRequest,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileInsertResponse | JSONResponse:
    """插入对话到 Memobase 缓冲区，自动提取画像"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        return await service.insert(user_id=request.user_id, messages=messages, sync=request.sync)
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/flush", response_model=ProfileFlushResponse, responses={502: {"model": ErrorResponse}}
)
async def flush_profile(
    request: ProfileFlushRequest,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileFlushResponse | JSONResponse:
    """触发缓冲区处理"""
    try:
        return await service.flush(user_id=request.user_id, sync=request.sync)
    except EngineError as e:
        return _engine_error_response(e)


@router.get(
    "/{user_id}", response_model=ProfileGetResponse, responses={502: {"model": ErrorResponse}}
)
async def get_profile(
    user_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileGetResponse | JSONResponse:
    """获取用户结构化画像"""
    try:
        return await service.get_profile(user_id)
    except EngineError as e:
        return _engine_error_response(e)


@router.post(
    "/{user_id}/context",
    response_model=ProfileContextResponse,
    responses={502: {"model": ErrorResponse}},
)
async def get_context(
    user_id: str,
    request: ProfileContextRequest,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileContextResponse | JSONResponse:
    """获取上下文提示词"""
    try:
        chats = None
        if request.chats:
            chats = [{"role": m.role, "content": m.content} for m in request.chats]
        return await service.get_context(
            user_id=user_id, max_token_size=request.max_token_size, chats=chats
        )
    except EngineError as e:
        return _engine_error_response(e)
