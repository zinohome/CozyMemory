"""API 依赖注入

提供客户端和服务单例的 FastAPI 依赖注入函数。
"""

from ..clients.cognee import CogneeClient
from ..clients.mem0 import Mem0Client
from ..clients.memobase import MemobaseClient
from ..config import settings
from ..services.conversation import ConversationService
from ..services.knowledge import KnowledgeService
from ..services.profile import ProfileService

# 客户端单例（延迟初始化）
_mem0_client: Mem0Client | None = None
_memobase_client: MemobaseClient | None = None
_cognee_client: CogneeClient | None = None


def get_mem0_client() -> Mem0Client:
    """获取 Mem0 客户端单例"""
    global _mem0_client
    if _mem0_client is None:
        _mem0_client = Mem0Client(
            api_url=settings.MEM0_API_URL,
            api_key=settings.MEM0_API_KEY or None,
            timeout=settings.MEM0_TIMEOUT,
        )
    return _mem0_client


def get_memobase_client() -> MemobaseClient:
    """获取 Memobase 客户端单例"""
    global _memobase_client
    if _memobase_client is None:
        _memobase_client = MemobaseClient(
            api_url=settings.MEMOBASE_API_URL,
            api_key=settings.MEMOBASE_API_KEY,
            timeout=settings.MEMOBASE_TIMEOUT,
        )
    return _memobase_client


def get_cognee_client() -> CogneeClient:
    """获取 Cognee 客户端单例"""
    global _cognee_client
    if _cognee_client is None:
        _cognee_client = CogneeClient(
            api_url=settings.COGNEE_API_URL,
            api_key=settings.COGNEE_API_KEY or None,
            timeout=settings.COGNEE_TIMEOUT,
        )
    return _cognee_client


async def close_all_clients() -> None:
    """关闭所有引擎客户端的 HTTP 连接（供应用关闭时调用）。"""
    if _mem0_client:
        await _mem0_client.close()
    if _memobase_client:
        await _memobase_client.close()
    if _cognee_client:
        await _cognee_client.close()


def get_conversation_service() -> ConversationService:
    """获取会话记忆服务"""
    return ConversationService(client=get_mem0_client())


def get_profile_service() -> ProfileService:
    """获取用户画像服务"""
    return ProfileService(client=get_memobase_client())


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务"""
    return KnowledgeService(client=get_cognee_client())
