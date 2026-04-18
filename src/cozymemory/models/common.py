"""通用数据模型

包含 Message、EngineStatus、HealthResponse、ErrorResponse。
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Message(BaseModel):
    """对话消息（Mem0 和 Memobase 共用）"""

    role: str = Field(..., description="角色: user / assistant / system")
    content: str = Field(..., description="消息内容")
    created_at: str | None = Field(None, description="消息时间戳 (ISO 8601)")


class EngineStatus(BaseModel):
    """引擎健康状态"""

    name: str = Field(..., description="引擎名称")
    status: str = Field(..., description="状态: healthy / unhealthy")
    latency_ms: float | None = Field(None, description="响应延迟(ms)")
    error: str | None = Field(None, description="错误信息")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="整体状态: healthy / degraded / unhealthy")
    engines: dict[str, EngineStatus] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ErrorResponse(BaseModel):
    """错误响应"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "error": "Mem0Error",
                "detail": "upstream timeout after 3 retries",
                "engine": "Mem0",
            }
        }
    }

    success: bool = False
    error: str = Field(..., description="错误类型")
    detail: str | None = Field(None, description="错误详情")
    engine: str | None = Field(None, description="出错的引擎名称")
