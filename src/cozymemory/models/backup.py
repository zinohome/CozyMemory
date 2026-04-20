"""备份/恢复 用户记忆的数据模型"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .conversation import ConversationMemory
from .profile import ProfileTopic


class DatasetDump(BaseModel):
    """单个 Cognee 数据集的文本快照"""

    name: str = Field(..., description="数据集名")
    documents: list[str] = Field(
        default_factory=list,
        description="从 DocumentChunk 节点提取的原文片段；导入时会重新 add+cognify",
    )


class MemoryBundle(BaseModel):
    """单用户记忆导出包。可选附带 Cognee 数据集（数据集与用户无关）。"""

    version: str = Field("1.0", description="Schema 版本")
    exported_at: datetime = Field(..., description="导出时间")
    user_id: str = Field(..., description="记忆所属用户 ID")
    conversations: list[ConversationMemory] = Field(
        default_factory=list, description="Mem0 对话记忆快照"
    )
    profile_topics: list[ProfileTopic] = Field(
        default_factory=list, description="Memobase 用户画像主题"
    )
    datasets: list[DatasetDump] = Field(
        default_factory=list, description="Cognee 数据集（用户独立）"
    )


class BackupImportRequest(BaseModel):
    """导入请求体"""

    bundle: MemoryBundle = Field(..., description="完整导出包")
    target_user_id: str | None = Field(
        None,
        description="可选重映射目标；为空则用 bundle.user_id。允许把一个账号的记忆导入到另一个账号",
    )


class BackupImportResponse(BaseModel):
    """导入结果"""

    success: bool = True
    user_id: str
    conversations_imported: int = 0
    conversations_skipped: int = 0
    profiles_imported: int = 0
    profiles_skipped: int = 0
    datasets_imported: int = 0
    documents_imported: int = 0
    datasets_skipped: int = 0
    errors: list[dict[str, Any]] = Field(
        default_factory=list, description="每条失败记录的 kind + id + reason"
    )
