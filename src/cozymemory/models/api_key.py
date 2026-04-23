"""API Key Dashboard API 请求/响应模型。"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {"name": "production-backend", "environment": "live"}
        }
    }

    name: str = Field(..., min_length=1, max_length=100)
    environment: Literal["live", "test"] = Field(
        default="live", description="live=生产 test=沙箱（可做配额/QPS 区分）"
    )


class ApiKeyUpdate(BaseModel):
    model_config = {"json_schema_extra": {"example": {"disabled": True}}}

    name: str | None = Field(default=None, min_length=1, max_length=100)
    disabled: bool | None = None


class ApiKeyInfo(BaseModel):
    """不包含明文 key，只给 list / get / update 用。"""

    id: UUID
    app_id: UUID
    name: str
    prefix: str = Field(..., description="展示用前缀，如 cozy_live_abc12345")
    environment: str
    disabled: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None


class ApiKeyCreateResponse(BaseModel):
    """create / rotate 响应。明文 key 只此一次返回，丢失只能 rotate 重发。"""

    record: ApiKeyInfo
    key: str = Field(..., description="明文 API Key，保存好，不会再显示")


class ApiKeyListResponse(BaseModel):
    success: bool = True
    data: list[ApiKeyInfo] = Field(default_factory=list)
    total: int = 0
