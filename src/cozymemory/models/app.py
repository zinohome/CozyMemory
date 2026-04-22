"""App CRUD 的请求 / 响应 Pydantic 模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AppCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Douyin Memory",
                "slug": "douyin-memory",
                "description": "抖音用户记忆服务",
            }
        }
    }

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="URL 友好，小写字母 + 数字 + 短横线；同 org 内唯一",
    )
    description: str = Field(default="", max_length=1000)


class AppUpdate(BaseModel):
    """只允许改 name / description。slug 和 namespace_id 不变（影响用户 UUID 映射）。"""

    model_config = {"json_schema_extra": {"example": {"name": "New Name"}}}

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)


class AppInfo(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    slug: str
    namespace_id: UUID = Field(..., description="用于 uuid5 的 namespace，永不变")
    description: str
    created_at: datetime


class AppListResponse(BaseModel):
    success: bool = True
    data: list[AppInfo] = Field(default_factory=list)
    total: int = 0
