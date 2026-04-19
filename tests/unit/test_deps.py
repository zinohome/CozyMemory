"""依赖注入测试"""

from unittest.mock import patch

import cozymemory.api.deps as deps_module
from cozymemory.api.deps import (
    get_cognee_client,
    get_conversation_service,
    get_knowledge_service,
    get_mem0_client,
    get_memobase_client,
    get_profile_service,
    get_user_mapping_service,
)
from cozymemory.clients.cognee import CogneeClient
from cozymemory.clients.mem0 import Mem0Client
from cozymemory.clients.memobase import MemobaseClient
from cozymemory.services.conversation import ConversationService
from cozymemory.services.knowledge import KnowledgeService
from cozymemory.services.profile import ProfileService
from cozymemory.services.user_mapping import UserMappingService


def setup_function():
    """每个测试前重置单例"""
    deps_module._mem0_client = None
    deps_module._memobase_client = None
    deps_module._cognee_client = None
    deps_module._redis_client = None
    deps_module._user_mapping_service = None


def test_get_mem0_client_creates_singleton():
    """get_mem0_client 创建单例"""
    setup_function()
    client = get_mem0_client()
    assert isinstance(client, Mem0Client)
    # 第二次调用返回同一个实例
    client2 = get_mem0_client()
    assert client is client2


def test_get_memobase_client_creates_singleton():
    """get_memobase_client 创建单例"""
    setup_function()
    client = get_memobase_client()
    assert isinstance(client, MemobaseClient)
    client2 = get_memobase_client()
    assert client is client2


def test_get_cognee_client_creates_singleton():
    """get_cognee_client 创建单例"""
    setup_function()
    client = get_cognee_client()
    assert isinstance(client, CogneeClient)
    client2 = get_cognee_client()
    assert client is client2


def test_get_conversation_service():
    """get_conversation_service 返回 ConversationService"""
    setup_function()
    service = get_conversation_service()
    assert isinstance(service, ConversationService)
    assert isinstance(service.client, Mem0Client)


def test_get_profile_service():
    """get_profile_service 返回 ProfileService（含 UserMappingService）"""
    setup_function()
    service = get_profile_service()
    assert isinstance(service, ProfileService)
    assert isinstance(service.client, MemobaseClient)
    assert isinstance(service._mapping, UserMappingService)


def test_get_user_mapping_service():
    """get_user_mapping_service 返回 UserMappingService"""
    setup_function()
    svc = get_user_mapping_service()
    assert isinstance(svc, UserMappingService)


def test_get_knowledge_service():
    """get_knowledge_service 返回 KnowledgeService"""
    setup_function()
    service = get_knowledge_service()
    assert isinstance(service, KnowledgeService)
    assert isinstance(service.client, CogneeClient)


def test_get_mem0_client_with_custom_settings():
    """get_mem0_client 使用 settings 配置"""
    setup_function()
    with patch("cozymemory.api.deps.settings") as mock_settings:
        mock_settings.MEM0_API_URL = "http://custom:8888"
        mock_settings.MEM0_API_KEY = "custom-key"
        mock_settings.MEM0_TIMEOUT = 60.0
        client = get_mem0_client()
        assert client.api_url == "http://custom:8888"
        assert client.api_key == "custom-key"
        assert client.timeout == 60.0


def test_get_memobase_client_with_custom_settings():
    """get_memobase_client 使用 settings 配置"""
    setup_function()
    with patch("cozymemory.api.deps.settings") as mock_settings:
        mock_settings.MEMOBASE_API_URL = "http://custom:8019"
        mock_settings.MEMOBASE_API_KEY = "my-token"
        mock_settings.MEMOBASE_TIMEOUT = 120.0
        client = get_memobase_client()
        assert client.api_url == "http://custom:8019"
        assert client.api_key == "my-token"
