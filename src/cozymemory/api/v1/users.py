"""用户 ID 映射 REST API 端点

提供 user_id ↔ UUID 的查询与管理接口，
供调试和跨系统 ID 对齐使用。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ...api.deps import get_user_mapping_service
from ...models.common import ErrorResponse
from ...services.user_mapping import UserMappingService

router = APIRouter(prefix="/users", tags=["users"])


class UserMappingResponse(BaseModel):
    success: bool = True
    user_id: str
    uuid: str


class UserMappingDeleteResponse(BaseModel):
    success: bool
    message: str


@router.get(
    "/{user_id}/uuid",
    response_model=UserMappingResponse,
    responses={200: {"description": "返回（或新建）该 user_id 对应的 UUID v4"}},
    summary="获取或创建用户 UUID 映射",
)
async def get_or_create_uuid(
    user_id: str,
    service: UserMappingService = Depends(get_user_mapping_service),
) -> UserMappingResponse:
    """查询 user_id 对应的 UUID v4 映射；若不存在则自动创建。

    Memobase 要求 user_id 必须是 UUID v4，本接口隐藏该细节。
    """
    uuid_str = await service.get_or_create_uuid(user_id)
    return UserMappingResponse(user_id=user_id, uuid=uuid_str)


@router.get(
    "/{user_id}/uuid/lookup",
    response_model=UserMappingResponse,
    responses={
        404: {"model": ErrorResponse, "description": "映射不存在"},
    },
    summary="查询用户 UUID 映射（不自动创建）",
)
async def lookup_uuid(
    user_id: str,
    service: UserMappingService = Depends(get_user_mapping_service),
) -> UserMappingResponse | JSONResponse:
    """仅查询已存在的映射，若不存在返回 404（不自动创建新 UUID）。"""
    uuid_str = await service.get_uuid(user_id)
    if uuid_str is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                success=False,
                error="NotFoundError",
                detail=f"user_id '{user_id}' 的 UUID 映射不存在",
            ).model_dump(),
        )
    return UserMappingResponse(user_id=user_id, uuid=uuid_str)


@router.delete(
    "/{user_id}/uuid",
    response_model=UserMappingDeleteResponse,
    summary="删除用户 UUID 映射",
)
async def delete_uuid_mapping(
    user_id: str,
    service: UserMappingService = Depends(get_user_mapping_service),
) -> UserMappingDeleteResponse:
    """删除 user_id 的 UUID 映射记录（不影响 Memobase 实际数据）。

    下次调用画像接口时会自动生成新的 UUID（映射到新的 Memobase 用户）。
    若需要彻底清除数据，请同时调用 DELETE /api/v1/profiles/{user_id}。
    """
    existed = await service.delete_mapping(user_id)
    if existed:
        return UserMappingDeleteResponse(success=True, message="映射已删除")
    return UserMappingDeleteResponse(success=True, message="映射不存在，无需删除")
