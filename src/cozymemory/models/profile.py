"""用户画像数据模型

对应引擎：Memobase
核心范式：插入对话 (insert) → 缓冲区 (buffer) → LLM 处理 (flush) → 生成画像 (profile)
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .common import Message


class ProfileInsertRequest(BaseModel):
    """插入对话到 Memobase 缓冲区"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    messages: list[Message] = Field(..., description="对话消息列表", min_length=1)
    sync: bool = Field(False, description="是否同步等待处理完成")


class ProfileFlushRequest(BaseModel):
    """触发缓冲区处理"""

    user_id: str = Field(..., description="用户 ID", min_length=1)
    sync: bool = Field(False, description="是否同步等待处理完成")


class ProfileContextRequest(BaseModel):
    """获取上下文提示词请求（user_id 来自路径参数）"""

    max_token_size: int = Field(500, ge=100, le=4000, description="上下文最大 token 数")
    chats: list[Message] | None = Field(None, description="近期对话（用于语义搜索匹配）")


class ProfileTopic(BaseModel):
    """画像中的单个主题条目"""

    id: str = Field(..., description="条目 ID")
    topic: str = Field(..., description="主题 (如 basic_info, interest)")
    sub_topic: str = Field(..., description="子主题 (如 name, hobby)")
    content: str = Field(..., description="内容")
    created_at: datetime | None = Field(None)
    updated_at: datetime | None = Field(None)


class UserProfile(BaseModel):
    """完整用户画像"""

    user_id: str = Field(..., description="用户 ID")
    topics: list[ProfileTopic] = Field(default_factory=list, description="画像主题列表")
    updated_at: datetime | None = Field(None)


class ProfileContext(BaseModel):
    """上下文提示词结果"""

    user_id: str = Field(..., description="用户 ID")
    context: str = Field(..., description="可直接插入 LLM prompt 的文本")


class ProfileInsertResponse(BaseModel):
    """插入响应"""

    success: bool = True
    user_id: str
    blob_id: str | None = Field(None, description="Blob ID")
    message: str = ""


class ProfileFlushResponse(BaseModel):
    """缓冲区处理响应"""

    success: bool = True
    message: str = ""


class ProfileGetResponse(BaseModel):
    """获取画像响应"""

    success: bool = True
    data: UserProfile | None = Field(None, description="用户画像数据")
    message: str = ""


class ProfileContextResponse(BaseModel):
    """获取上下文响应"""

    success: bool = True
    data: ProfileContext | None = Field(None, description="上下文提示词")
    message: str = ""


class ProfileAddItemResponse(BaseModel):
    """手动添加画像条目响应"""

    success: bool = True
    data: ProfileTopic | None = Field(None, description="添加的画像条目")
    message: str = ""


class ProfileDeleteItemResponse(BaseModel):
    """删除画像条目响应"""

    success: bool
    message: str = ""
