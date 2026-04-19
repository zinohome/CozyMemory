"""gRPC 集成测试

针对真实运行的 CozyMemory gRPC 服务（默认 localhost:50051）执行端到端验证。
覆盖全部 4 个 Service 的核心方法。

环境变量：
  COZY_GRPC_HOST  — gRPC 服务地址（默认 localhost）
  COZY_GRPC_PORT  — gRPC 服务端口（默认 50051）

依赖：grpcio（已在 requirements.txt 中）
"""

import asyncio
import os
import uuid

import grpc
import pytest

from cozymemory.grpc_server import (
    context_pb2,
    context_pb2_grpc,
    conversation_pb2,
    conversation_pb2_grpc,
    knowledge_pb2,
    knowledge_pb2_grpc,
    profile_pb2,
    profile_pb2_grpc,
)

GRPC_HOST = os.getenv("COZY_GRPC_HOST", "localhost")
GRPC_PORT = int(os.getenv("COZY_GRPC_PORT", "50051"))
GRPC_TARGET = f"{GRPC_HOST}:{GRPC_PORT}"


def _grpc_reachable() -> bool:
    channel = grpc.insecure_channel(GRPC_TARGET)
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
        return True
    except Exception:
        return False
    finally:
        channel.close()


_grpc_up: bool | None = None


def grpc_is_up() -> bool:
    global _grpc_up
    if _grpc_up is None:
        _grpc_up = _grpc_reachable()
    return _grpc_up


requires_grpc = pytest.mark.skipif(
    not grpc_is_up(),
    reason=f"gRPC server not reachable at {GRPC_TARGET}",
)


@pytest.fixture
async def grpc_channel():
    """异步 gRPC channel，支持 await stub.Method(...)"""
    channel = grpc.aio.insecure_channel(GRPC_TARGET)
    yield channel
    await channel.close()


# ══════════════════════════════════════════════════════════════════════════════
# ConversationService
# ══════════════════════════════════════════════════════════════════════════════

CONV_USER = "grpc-test-user"


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_add_conversation(grpc_channel):
    """ConversationService.AddConversation 成功添加对话"""
    stub = conversation_pb2_grpc.ConversationServiceStub(grpc_channel)
    request = conversation_pb2.AddConversationRequest(
        user_id=CONV_USER,
        messages=[conversation_pb2.Message(role="user", content="我喜欢踢足球，这是 gRPC 测试")],
        infer=True,
    )
    response = await stub.AddConversation(request, timeout=30)
    assert response.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_list_conversations(grpc_channel):
    """ConversationService.ListConversations 返回记忆列表"""
    stub = conversation_pb2_grpc.ConversationServiceStub(grpc_channel)
    request = conversation_pb2.ListConversationsRequest(user_id=CONV_USER, limit=10)
    response = await stub.ListConversations(request, timeout=30)
    assert response.success is True
    assert isinstance(list(response.data), list)


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_search_conversations(grpc_channel):
    """ConversationService.SearchConversations 语义搜索"""
    stub = conversation_pb2_grpc.ConversationServiceStub(grpc_channel)
    request = conversation_pb2.SearchConversationsRequest(
        user_id=CONV_USER,
        query="运动爱好",
        limit=5,
    )
    response = await stub.SearchConversations(request, timeout=30)
    assert response.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_add_get_delete_conversation(grpc_channel):
    """ConversationService: AddConversation → GetConversation → DeleteConversation"""
    stub = conversation_pb2_grpc.ConversationServiceStub(grpc_channel)
    user_id = f"grpc-crud-{uuid.uuid4().hex[:8]}"

    # Add
    add_resp = await stub.AddConversation(
        conversation_pb2.AddConversationRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="这条记忆用于 gRPC CRUD 测试")],
            infer=True,
        ),
        timeout=30,
    )
    assert add_resp.success is True
    memories = list(add_resp.data)
    if not memories:
        pytest.skip("Mem0 未提取到记忆，跳过 get/delete 验证")

    memory_id = memories[0].id

    # Get
    get_resp = await stub.GetConversation(
        conversation_pb2.GetConversationRequest(memory_id=memory_id),
        timeout=30,
    )
    assert get_resp.id == memory_id

    # Delete single
    del_resp = await stub.DeleteConversation(
        conversation_pb2.DeleteConversationRequest(memory_id=memory_id),
        timeout=30,
    )
    assert del_resp.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_delete_all_conversations(grpc_channel):
    """ConversationService.DeleteAllConversations 清空用户记忆"""
    stub = conversation_pb2_grpc.ConversationServiceStub(grpc_channel)
    response = await stub.DeleteAllConversations(
        conversation_pb2.DeleteAllConversationsRequest(user_id=CONV_USER),
        timeout=30,
    )
    assert response.success is True


# ══════════════════════════════════════════════════════════════════════════════
# ProfileService
# ══════════════════════════════════════════════════════════════════════════════


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_insert_profile(grpc_channel):
    """ProfileService.InsertProfile 成功插入对话"""
    stub = profile_pb2_grpc.ProfileServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    response = await stub.InsertProfile(
        profile_pb2.InsertProfileRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="我叫 gRPC 测试用户")],
            sync=True,
        ),
        timeout=60,
    )
    assert response.success is True
    assert response.user_id == user_id


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_flush_profile(grpc_channel):
    """ProfileService.FlushProfile 触发缓冲区处理"""
    stub = profile_pb2_grpc.ProfileServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    # Insert first
    await stub.InsertProfile(
        profile_pb2.InsertProfileRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="测试 flush")],
            sync=False,
        ),
        timeout=30,
    )
    # Flush
    response = await stub.FlushProfile(
        profile_pb2.FlushProfileRequest(user_id=user_id, sync=True),
        timeout=30,
    )
    assert response.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_get_profile(grpc_channel):
    """ProfileService.GetProfile 返回用户画像结构"""
    stub = profile_pb2_grpc.ProfileServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    await stub.InsertProfile(
        profile_pb2.InsertProfileRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="我住在深圳，是一名工程师")],
            sync=True,
        ),
        timeout=60,
    )
    response = await stub.GetProfile(
        profile_pb2.GetProfileRequest(user_id=user_id),
        timeout=30,
    )
    assert response.user_id == user_id
    assert isinstance(list(response.topics), list)


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_get_context(grpc_channel):
    """ProfileService.GetContext 返回 LLM-ready 上下文字符串"""
    stub = profile_pb2_grpc.ProfileServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    await stub.InsertProfile(
        profile_pb2.InsertProfileRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="我叫张三，喜欢旅行")],
            sync=True,
        ),
        timeout=60,
    )
    response = await stub.GetContext(
        profile_pb2.GetContextRequest(user_id=user_id, max_token_size=300),
        timeout=30,
    )
    assert response.success is True
    assert response.user_id == user_id
    assert isinstance(response.context, str)


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_add_and_delete_profile_item(grpc_channel):
    """ProfileService: AddProfileItem → DeleteProfileItem"""
    stub = profile_pb2_grpc.ProfileServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())

    # Memobase requires user to exist (FK constraint) — create via InsertProfile first
    await stub.InsertProfile(
        profile_pb2.InsertProfileRequest(
            user_id=user_id,
            messages=[conversation_pb2.Message(role="user", content="初始化用户")],
            sync=True,
        ),
        timeout=60,
    )

    add_resp = await stub.AddProfileItem(
        profile_pb2.AddProfileItemRequest(
            user_id=user_id,
            topic="interest",
            sub_topic="sport",
            content="喜欢游泳（gRPC 测试）",
        ),
        timeout=30,
    )
    assert add_resp.success is True
    profile_id = add_resp.data.id
    assert profile_id

    del_resp = await stub.DeleteProfileItem(
        profile_pb2.DeleteProfileItemRequest(user_id=user_id, profile_id=profile_id),
        timeout=30,
    )
    assert del_resp.success is True


# ══════════════════════════════════════════════════════════════════════════════
# KnowledgeService
# ══════════════════════════════════════════════════════════════════════════════


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_list_datasets(grpc_channel):
    """KnowledgeService.ListDatasets 返回数据集列表"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    response = await stub.ListDatasets(
        knowledge_pb2.ListDatasetsRequest(),
        timeout=30,
    )
    assert response.success is True
    assert isinstance(list(response.data), list)


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_create_dataset(grpc_channel):
    """KnowledgeService.CreateDataset 创建新数据集"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    ds_name = f"grpc-test-{uuid.uuid4().hex[:8]}"
    response = await stub.CreateDataset(
        knowledge_pb2.CreateDatasetRequest(name=ds_name),
        timeout=30,
    )
    assert response.name == ds_name


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_add_knowledge(grpc_channel):
    """KnowledgeService.AddKnowledge 添加文档"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    ds_name = f"grpc-add-{uuid.uuid4().hex[:8]}"
    response = await stub.AddKnowledge(
        knowledge_pb2.AddKnowledgeRequest(
            data="CozyMemory gRPC 集成测试文档，验证知识库添加功能。",
            dataset=ds_name,
        ),
        timeout=30,
    )
    assert response.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_cognify(grpc_channel):
    """KnowledgeService.Cognify 触发知识图谱构建"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    ds_name = f"grpc-cognify-{uuid.uuid4().hex[:8]}"

    # 先添加文档
    await stub.AddKnowledge(
        knowledge_pb2.AddKnowledgeRequest(
            data="CozyMemory 是统一 AI 记忆平台，整合 Mem0、Memobase、Cognee。",
            dataset=ds_name,
        ),
        timeout=30,
    )

    response = await stub.Cognify(
        knowledge_pb2.CognifyRequest(datasets=[ds_name], run_in_background=True),
        timeout=60,
    )
    assert response.success is True


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_full_knowledge_flow(grpc_channel):
    """KnowledgeService: AddKnowledge → Cognify → 轮询 SearchKnowledge（最多 120s）"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    ds_name = f"grpc-flow-{uuid.uuid4().hex[:8]}"
    content = "gRPC 全流程测试：CozyMemory 整合三大 AI 记忆引擎。"

    # Add
    add_resp = await stub.AddKnowledge(
        knowledge_pb2.AddKnowledgeRequest(data=content, dataset=ds_name),
        timeout=30,
    )
    assert add_resp.success is True

    # Cognify
    cognify_resp = await stub.Cognify(
        knowledge_pb2.CognifyRequest(datasets=[ds_name], run_in_background=True),
        timeout=60,
    )
    assert cognify_resp.success is True

    # Poll search — 最多 120s
    found = False
    for _ in range(12):
        await asyncio.sleep(10)
        search_resp = await stub.SearchKnowledge(
            knowledge_pb2.SearchKnowledgeRequest(
                query="CozyMemory 整合哪些引擎",
                dataset=ds_name,
                search_type="CHUNKS",
                top_k=5,
            ),
            timeout=30,
        )
        assert search_resp.success is True
        if list(search_resp.data):
            found = True
            break

    assert found, "gRPC: Cognify 完成后 120s 内未搜索到结果"


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_search_knowledge(grpc_channel):
    """KnowledgeService.SearchKnowledge 基本搜索"""
    stub = knowledge_pb2_grpc.KnowledgeServiceStub(grpc_channel)
    response = await stub.SearchKnowledge(
        knowledge_pb2.SearchKnowledgeRequest(
            query="AI 记忆",
            search_type="CHUNKS",
            top_k=5,
        ),
        timeout=30,
    )
    assert response.success is True
    assert isinstance(list(response.data), list)


# ══════════════════════════════════════════════════════════════════════════════
# ContextService
# ══════════════════════════════════════════════════════════════════════════════


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_get_unified_context(grpc_channel):
    """ContextService.GetUnifiedContext 三引擎并发返回"""
    stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
    user_id = f"grpc-ctx-{uuid.uuid4().hex[:8]}"
    response = await stub.GetUnifiedContext(
        context_pb2.GetUnifiedContextRequest(
            user_id=user_id,
            query="用户喜欢什么",
            include_conversations=True,
            include_profile=True,
            include_knowledge=True,
            conversation_limit=5,
            max_token_size=300,
            knowledge_top_k=3,
            knowledge_search_type="CHUNKS",
        ),
        timeout=60,
    )
    assert response.success is True
    assert response.user_id == user_id
    assert response.latency_ms >= 0
    assert isinstance(dict(response.errors), dict)


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_get_unified_context_no_query(grpc_channel):
    """ContextService.GetUnifiedContext query 为空时 knowledge 跳过"""
    stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    response = await stub.GetUnifiedContext(
        context_pb2.GetUnifiedContextRequest(
            user_id=user_id,
            include_conversations=True,
            include_profile=False,
            include_knowledge=True,
            conversation_limit=5,
            max_token_size=300,
            knowledge_top_k=3,
            knowledge_search_type="CHUNKS",
        ),
        timeout=30,
    )
    assert response.success is True
    assert list(response.knowledge) == []


@requires_grpc
@pytest.mark.asyncio
async def test_grpc_get_unified_context_with_chats(grpc_channel):
    """ContextService.GetUnifiedContext 携带 chats 参数"""
    stub = context_pb2_grpc.ContextServiceStub(grpc_channel)
    user_id = str(uuid.uuid4())
    response = await stub.GetUnifiedContext(
        context_pb2.GetUnifiedContextRequest(
            user_id=user_id,
            include_conversations=False,
            include_profile=True,
            include_knowledge=False,
            max_token_size=200,
            chats=[conversation_pb2.Message(role="user", content="你好")],
        ),
        timeout=30,
    )
    assert response.success is True
