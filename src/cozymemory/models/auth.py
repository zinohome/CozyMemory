"""Auth API 请求 / 响应模型。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册：同时创建 Organization + Developer(owner)"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "alice@bytedance.com",
                "password": "SuperSecret123",
                "org_name": "ByteDance",
                "org_slug": "bytedance",
                "name": "Alice",
            }
        }
    }

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72, description="bcrypt 最长 72 字节")
    org_name: str = Field(..., min_length=1, max_length=200)
    org_slug: str = Field(
        ...,
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
        description="URL 友好，小写字母 + 数字 + 短横线",
    )
    name: str = Field(default="", max_length=100, description="开发者显示名（可选）")


class LoginRequest(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"email": "alice@bytedance.com", "password": "SuperSecret123"}}
    }

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class DeveloperInfo(BaseModel):
    """返回给前端的开发者信息（不含密码）"""

    id: UUID
    email: str
    name: str
    role: str
    org_id: UUID
    org_name: str
    org_slug: str
    is_active: bool
    last_login_at: datetime | None


class TokenResponse(BaseModel):
    """登录 / 注册成功的响应。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="秒")
    developer: DeveloperInfo
