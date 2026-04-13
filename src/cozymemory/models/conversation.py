"""会话记忆数据模型

对应引擎：Mem0
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import Message


class ConversationMemoryCreate(BaseModel):
    """添加对话请求 → Mem0 自动提取事实"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(..., description="对话消息列表", min_length=1)
    metadata: dict[str, Any] | None = Field(None, description="元数据 (source, session_id 等)")
    infer: bool = Field(True, description="是否使用 LLM 提取事实。False 则原样存储")


class ConversationMemorySearch(BaseModel):
    """搜索会话记忆"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    query: str = Field(..., description="搜索查询文本", min_length=1)
    limit: int = Field(10, ge=1, le=100, description="返回数量限制")
    threshold: float | None = Field(None, ge=0, le=1, description="最低相似度阈值")


class ConversationMemory(BaseModel):
    """Mem0 返回的单条记忆（提取出的事实）"""

    id: str = Field(..., description="记忆 ID")
    user_id: str = Field(..., description="用户 ID")
    content: str = Field(..., description="提取的事实内容")
    score: float | None = Field(None, description="搜索相似度分数")
    metadata: dict[str, Any] | None = Field(None, description="元数据")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")


class ConversationMemoryListResponse(BaseModel):
    """记忆列表响应"""

    success: bool = True
    data: list[ConversationMemory] = Field(default_factory=list)
    total: int = Field(0, description="总数")
    message: str = ""
