"""API Key 管理相关模型"""

from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyRecord(BaseModel):
    """服务端存储的 API key 元数据（不含明文和 hash）"""

    id: str = Field(..., description="key ID（UUID）")
    name: str = Field(..., description="人可读命名")
    prefix: str = Field(..., description="key 前缀，供识别，例如 cozy_prod_a1b2c3")
    created_at: datetime = Field(..., description="创建时间")
    last_used_at: datetime | None = Field(None, description="最近一次成功鉴权时间")
    disabled: bool = Field(False, description="禁用后不再通过鉴权")


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="人可读命名")


class ApiKeyCreateResponse(BaseModel):
    """创建/轮换响应 — 仅此刻返回明文 key，用户必须立即保存"""

    record: ApiKeyRecord
    key: str = Field(..., description="明文 key（仅此次返回，之后只存 hash）")


class ApiKeyUpdateRequest(BaseModel):
    name: str | None = Field(None, max_length=64)
    disabled: bool | None = None


class ApiKeyListResponse(BaseModel):
    success: bool = True
    data: list[ApiKeyRecord]
    total: int = 0
