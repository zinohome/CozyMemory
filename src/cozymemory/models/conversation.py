"""会话记忆数据模型

对应引擎：Mem0
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import Message

MemoryScope = Literal["short", "long", "both"]
"""记忆范围：
- short  仅当前 session（短期记忆）
- long   跨 session 的全量记忆（长期记忆，默认）
- both   同时返回短期和长期（ContextResponse 拆成两个列表）
"""


class ConversationMemoryCreate(BaseModel):
    """添加对话请求 → Mem0 自动提取事实"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_01",
                "agent_id": "sales-agent",
                "session_id": "sess_abc123",
                "messages": [
                    {"role": "user", "content": "我最近开始学打篮球，感觉很有趣"},
                    {"role": "assistant", "content": "太棒了！篮球是很好的运动"},
                ],
                "metadata": {"source": "web"},
                "infer": True,
            }
        }
    }

    user_id: str = Field(..., description="用户 ID", min_length=1)
    agent_id: str | None = Field(None, description="智能体 ID，按 agent 隔离记忆视角")
    session_id: str | None = Field(None, description="会话 ID，映射到 Mem0 run_id（短期记忆）")
    messages: list[Message] = Field(..., description="对话消息列表", min_length=1)
    metadata: dict[str, Any] | None = Field(None, description="元数据 (source 等)")
    infer: bool = Field(True, description="是否使用 LLM 提取事实。False 则原样存储")


class ConversationMemorySearch(BaseModel):
    """搜索会话记忆"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_01",
                "agent_id": "sales-agent",
                "session_id": "sess_abc123",
                "query": "用户喜欢什么运动",
                "limit": 5,
                "threshold": 0.7,
                "memory_scope": "long",
            }
        }
    }

    user_id: str = Field(..., description="用户 ID", min_length=1)
    agent_id: str | None = Field(None, description="限定智能体视角，None 则搜索该用户的全部记忆")
    session_id: str | None = Field(None, description="限定会话（memory_scope=short/both 时生效）")
    query: str = Field(..., description="搜索查询文本", min_length=1)
    limit: int = Field(10, ge=1, le=100, description="返回数量限制")
    threshold: float | None = Field(None, ge=0, le=1, description="最低相似度阈值")
    memory_scope: MemoryScope = Field(
        "long",
        description="记忆范围：short=仅本 session / long=全量历史（默认）/ both=两者均返回",
    )


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
