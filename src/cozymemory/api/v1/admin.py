"""Admin API — 动态 API Key 管理

鉴权边界：仅 bootstrap env key（COZY_API_KEYS）可访问 /admin/*，
动态 key 禁止调用（中间件里已过滤）。

路由：
  GET    /admin/api-keys          列表
  POST   /admin/api-keys          创建 → 明文 key 仅此次返回
  PATCH  /admin/api-keys/{id}     改名 / 启用禁用
  POST   /admin/api-keys/{id}/rotate 轮换 → 新明文 key 仅此次返回
  DELETE /admin/api-keys/{id}     删除
"""

from fastapi import APIRouter, Depends, HTTPException, status

from ...models.admin import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyRecord,
    ApiKeyUpdateRequest,
)
from ...services.api_keys import ApiKeyStore
from ..deps import get_api_key_store

router = APIRouter(prefix="/admin/api-keys", tags=["admin"])


@router.get("", response_model=ApiKeyListResponse)
async def list_keys(store: ApiKeyStore = Depends(get_api_key_store)) -> ApiKeyListResponse:
    records = await store.list_keys()
    return ApiKeyListResponse(data=records, total=len(records))


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreateRequest,
    store: ApiKeyStore = Depends(get_api_key_store),
) -> ApiKeyCreateResponse:
    return await store.create(name=body.name.strip())


@router.patch("/{key_id}", response_model=ApiKeyRecord)
async def update_key(
    key_id: str,
    body: ApiKeyUpdateRequest,
    store: ApiKeyStore = Depends(get_api_key_store),
) -> ApiKeyRecord:
    rec = await store.update(key_id, name=body.name, disabled=body.disabled)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="key not found")
    return rec


@router.post("/{key_id}/rotate", response_model=ApiKeyCreateResponse)
async def rotate_key(
    key_id: str,
    store: ApiKeyStore = Depends(get_api_key_store),
) -> ApiKeyCreateResponse:
    rec = await store.rotate(key_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="key not found")
    return rec


@router.delete("/{key_id}")
async def delete_key(
    key_id: str,
    store: ApiKeyStore = Depends(get_api_key_store),
) -> dict[str, bool]:
    ok = await store.delete(key_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="key not found")
    return {"success": True}
