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
    ProfileAddItemRequest,
    ProfileAddItemResponse,
    ProfileContextRequest,
    ProfileContextResponse,
    ProfileDeleteItemResponse,
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


@router.post(
    "/{user_id}/items",
    response_model=ProfileAddItemResponse,
    responses={502: {"model": ErrorResponse}},
)
async def add_profile_item(
    user_id: str,
    request: ProfileAddItemRequest,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileAddItemResponse | JSONResponse:
    """手动添加画像条目"""
    try:
        return await service.add_profile_item(
            user_id=user_id,
            topic=request.topic,
            sub_topic=request.sub_topic,
            content=request.content,
        )
    except EngineError as e:
        return _engine_error_response(e)


@router.delete(
    "/{user_id}/items/{profile_id}",
    response_model=ProfileDeleteItemResponse,
    responses={502: {"model": ErrorResponse}},
)
async def delete_profile_item(
    user_id: str,
    profile_id: str,
    service: ProfileService = Depends(get_profile_service),
) -> ProfileDeleteItemResponse | JSONResponse:
    """删除画像条目"""
    try:
        return await service.delete_profile_item(user_id=user_id, profile_id=profile_id)
    except EngineError as e:
        return _engine_error_response(e)
