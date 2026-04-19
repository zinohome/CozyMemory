"""用户 ID 映射 REST API 端点

提供 user_id ↔ UUID 的查询与管理接口，
供调试和跨系统 ID 对齐使用。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
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
    created: bool = False  # True 表示本次请求新建了映射


class UserMappingDeleteResponse(BaseModel):
    success: bool
    message: str
    warning: str = ""  # 数据安全提示


class UserListResponse(BaseModel):
    success: bool = True
    data: list[str]
    total: int


@router.get(
    "",
    response_model=UserListResponse,
    summary="列出所有已知用户",
)
async def list_users(
    service: UserMappingService = Depends(get_user_mapping_service),
) -> UserListResponse:
    """列出 Redis 中所有已建立 UUID 映射的 user_id，按字母排序。

    扫描 `cm:uid:*` 键空间，适用于用户管理和调试场景。
    """
    users = await service.list_users()
    return UserListResponse(data=users, total=len(users))


@router.get(
    "/{user_id}/uuid",
    response_model=UserMappingResponse,
    responses={
        200: {"description": "返回已有映射或（create=true 时）新建的 UUID v4"},
        404: {"model": ErrorResponse, "description": "映射不存在（create=false 时）"},
    },
    summary="查询用户 UUID 映射",
)
async def get_uuid(
    user_id: str,
    create: bool = Query(
        False,
        description=(
            "为 true 时：若映射不存在则自动创建（幂等）；"
            "为 false 时（默认）：映射不存在返回 404，不写入 Redis。"
        ),
    ),
    service: UserMappingService = Depends(get_user_mapping_service),
) -> UserMappingResponse | JSONResponse:
    """查询 user_id 对应的 UUID v4 映射。

    - `create=false`（默认）：只读，映射不存在返回 404。
    - `create=true`：若映射不存在则原子创建并返回，同时 `created=true` 标识本次新建。

    Memobase 要求 user_id 必须是 UUID v4，本接口供调试或预热映射使用。
    正常调用画像接口时映射会自动创建，无需手动调用。
    """
    if create:
        existing = await service.get_uuid(user_id)
        uuid_str = await service.get_or_create_uuid(user_id)
        return UserMappingResponse(user_id=user_id, uuid=uuid_str, created=(existing is None))

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
    """删除 user_id 的 Redis 映射记录。

    **警告**：此操作不会删除 Memobase 中的实际画像数据。
    删除映射后，下次调用画像接口将自动生成新的 UUID，旧 UUID 对应的
    Memobase 用户数据将永久无法通过 CozyMemory 接口访问（数据孤立）。

    若需彻底清除画像数据，请在删除映射前先调用
    `DELETE /api/v1/profiles/{user_id}/items/{profile_id}` 逐条删除，
    或通过 Memobase 直接操作。
    """
    existed = await service.delete_mapping(user_id)
    if existed:
        return UserMappingDeleteResponse(
            success=True,
            message="映射已删除",
            warning=(
                "Memobase 中该用户的历史画像数据已孤立，"
                "无法通过 CozyMemory 接口访问。"
            ),
        )
    return UserMappingDeleteResponse(success=True, message="映射不存在，无需删除")
