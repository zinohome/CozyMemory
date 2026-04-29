"""统一上下文数据模型

对应端点：POST /api/v1/context
一次请求并发获取 Mem0（对话记忆）、Memobase（用户画像）、Cognee（知识图谱）三种记忆。
"""

from pydantic import BaseModel, Field

from .common import Message
from .conversation import ConversationMemory, MemoryScope
from .knowledge import KnowledgeSearchResult, SearchType


class ContextRequest(BaseModel):
    """统一上下文请求"""

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_01",
                "agent_id": "sales-agent",
                "session_id": "sess_20260419_001",
                "query": "用户最近关心什么话题",
                "memory_scope": "both",
                "include_conversations": True,
                "include_profile": True,
                "include_knowledge": True,
                "conversation_limit": 5,
                "max_token_size": 500,
                "knowledge_datasets": ["product-catalog", "pricing"],
                "knowledge_top_k": 3,
                "knowledge_search_type": "GRAPH_COMPLETION",
                "engine_timeout": 5.0,
                "chats": [{"role": "user", "content": "你好，我最近喜欢游泳"}],
            }
        }
    }

    user_id: str = Field(
        ...,
        description="用户 ID。include_profile=true 时必须为 UUID v4（Memobase 限制）",
        min_length=1,
    )
    agent_id: str | None = Field(
        None,
        description="智能体 ID（如 sales-agent）。用于按 agent 隔离 Mem0 记忆视角",
    )
    session_id: str | None = Field(
        None,
        description="会话 ID。memory_scope=short/both 时用于短期记忆过滤",
    )
    query: str | None = Field(
        None,
        description=(
            "语义查询文本。有值时驱动 Mem0 语义搜索和 Cognee 知识检索；"
            "为 null 时 Mem0 返回全量记忆，Cognee 跳过"
        ),
        min_length=1,
    )
    memory_scope: MemoryScope = Field(
        "long",
        description=(
            "记忆范围：short=仅本 session 短期记忆 / "
            "long=全量历史长期记忆（默认）/ "
            "both=同时返回短期和长期（响应中拆分为 short_term_memories + long_term_memories）"
        ),
    )
    include_conversations: bool = Field(True, description="是否包含 Mem0 对话记忆")
    include_profile: bool = Field(True, description="是否包含 Memobase 用户画像上下文")
    include_knowledge: bool = Field(
        True, description="是否包含 Cognee 知识图谱结果（需提供 query）"
    )
    conversation_limit: int = Field(5, ge=1, le=100, description="Mem0 返回条数限制")
    max_token_size: int = Field(500, ge=100, le=4000, description="Memobase 上下文最大 token 数")
    knowledge_datasets: list[str] | None = Field(
        None,
        description="Cognee 查询的数据集列表。null 或空列表表示搜索全部数据集",
    )
    knowledge_top_k: int = Field(3, ge=1, le=50, description="Cognee 返回结果数量")
    knowledge_search_type: SearchType | None = Field(
        None, description="Cognee 搜索类型（null 时使用系统默认值 COGNEE_DEFAULT_SEARCH_TYPE）"
    )
    engine_timeout: float | None = Field(
        3.0,
        gt=0,
        description=(
            "每个引擎的超时时间（秒，默认 3s）。超时的引擎结果以错误形式记录在 errors 字段，"
            "不影响其他引擎的结果。设为 null 不限制"
        ),
    )
    chats: list[Message] | None = Field(
        None,
        description=(
            "当前对话轮次，传给 Memobase 以生成与当前对话更相关的上下文提示词。"
            "注意：Memobase context 端点当前为 GET-only，此参数透传至服务层但暂不生效"
        ),
    )


class ContextResponse(BaseModel):
    """统一上下文响应"""

    success: bool = True
    user_id: str = Field(..., description="用户 ID")
    conversations: list[ConversationMemory] = Field(
        default_factory=list,
        description=(
            "Mem0 对话记忆列表（向后兼容字段）。"
            "memory_scope=both 时等同于 long_term_memories"
        ),
    )
    short_term_memories: list[ConversationMemory] = Field(
        default_factory=list,
        description="当前 session 的短期记忆（memory_scope=short/both 时填充）",
    )
    long_term_memories: list[ConversationMemory] = Field(
        default_factory=list,
        description="跨 session 的长期记忆（memory_scope=long/both 时填充）",
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
