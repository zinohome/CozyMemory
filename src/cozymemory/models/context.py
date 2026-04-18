"""统一上下文数据模型

对应端点：POST /api/v1/context
一次请求并发获取 Mem0（对话记忆）、Memobase（用户画像）、Cognee（知识图谱）三种记忆。
"""

from pydantic import BaseModel, Field

from .conversation import ConversationMemory
from .knowledge import KnowledgeSearchResult, SearchType


class ContextRequest(BaseModel):
    """统一上下文请求"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "query": "用户最近关心什么话题",
                "include_conversations": True,
                "include_profile": True,
                "include_knowledge": True,
                "conversation_limit": 5,
                "max_token_size": 500,
                "knowledge_top_k": 3,
                "knowledge_search_type": "GRAPH_COMPLETION",
            }
        }
    }

    user_id: str = Field(
        ...,
        description="用户 ID。include_profile=true 时必须为 UUID v4（Memobase 限制）",
        min_length=1,
    )
    query: str | None = Field(
        None,
        description=(
            "语义查询文本。有值时驱动 Mem0 语义搜索和 Cognee 知识检索；"
            "为 null 时 Mem0 返回全量记忆，Cognee 跳过"
        ),
        min_length=1,
    )
    include_conversations: bool = Field(True, description="是否包含 Mem0 对话记忆")
    include_profile: bool = Field(True, description="是否包含 Memobase 用户画像上下文")
    include_knowledge: bool = Field(
        True, description="是否包含 Cognee 知识图谱结果（需提供 query）"
    )
    conversation_limit: int = Field(5, ge=1, le=100, description="Mem0 返回条数限制")
    max_token_size: int = Field(500, ge=100, le=4000, description="Memobase 上下文最大 token 数")
    knowledge_top_k: int = Field(3, ge=1, le=50, description="Cognee 返回结果数量")
    knowledge_search_type: SearchType = Field(
        "GRAPH_COMPLETION", description="Cognee 搜索类型"
    )


class ContextResponse(BaseModel):
    """统一上下文响应"""

    success: bool = True
    user_id: str = Field(..., description="用户 ID")
    conversations: list[ConversationMemory] = Field(
        default_factory=list, description="Mem0 对话记忆列表"
    )
    profile_context: str | None = Field(
        None, description="Memobase 生成的 LLM 上下文提示词，可直接插入 system prompt"
    )
    knowledge: list[KnowledgeSearchResult] = Field(
        default_factory=list, description="Cognee 知识图谱搜索结果"
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "各引擎的错误信息，键为引擎域名 (conversations/profile/knowledge)。"
            "有错误时对应字段返回空值，其他引擎结果不受影响"
        ),
    )
    latency_ms: float = Field(..., description="本次请求总耗时（毫秒），等于各引擎最长耗时")
