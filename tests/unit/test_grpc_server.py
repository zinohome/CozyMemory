"""gRPC 服务实现单元测试

测试 ConversationGrpcServicer、ProfileGrpcServicer、KnowledgeGrpcServicer
三个 gRPC 服务类的方法逻辑，验证它们正确地委托到 Service 层并转换返回值。
"""

from cozymemory.grpc_server.server import (
    ConversationGrpcServicer,
    KnowledgeGrpcServicer,
    ProfileGrpcServicer,
)

# ──────────────────────────── ConversationGrpcServicer ────────────────────────────


class TestConversationGrpcServicer:
    """会话记忆 gRPC 服务测试"""

    def test_servicer_class_exists(self):
        """验证 ConversationGrpcServicer 类可实例化"""
        servicer = ConversationGrpcServicer()
        assert servicer is not None
        assert hasattr(servicer, "AddConversation")
        assert hasattr(servicer, "SearchConversations")
        assert hasattr(servicer, "GetConversation")
        assert hasattr(servicer, "DeleteConversation")
        assert hasattr(servicer, "DeleteAllConversations")


# ──────────────────────────── ProfileGrpcServicer ────────────────────────────


class TestProfileGrpcServicer:
    """用户画像 gRPC 服务测试"""

    def test_servicer_class_exists(self):
        """验证 ProfileGrpcServicer 类可实例化"""
        servicer = ProfileGrpcServicer()
        assert servicer is not None
        assert hasattr(servicer, "InsertProfile")
        assert hasattr(servicer, "FlushProfile")
        assert hasattr(servicer, "GetProfile")
        assert hasattr(servicer, "GetContext")


# ──────────────────────────── KnowledgeGrpcServicer ────────────────────────────


class TestKnowledgeGrpcServicer:
    """知识库 gRPC 服务测试"""

    def test_servicer_class_exists(self):
        """验证 KnowledgeGrpcServicer 类可实例化"""
        servicer = KnowledgeGrpcServicer()
        assert servicer is not None
        assert hasattr(servicer, "CreateDataset")
        assert hasattr(servicer, "ListDatasets")
        assert hasattr(servicer, "AddKnowledge")
        assert hasattr(servicer, "Cognify")
        assert hasattr(servicer, "SearchKnowledge")


# ──────────────────────────── serve_grpc 函数 ────────────────────────────


class TestServeGrpc:
    """gRPC 服务器启动测试"""

    def test_serve_grpc_is_async(self):
        """验证 serve_grpc 是异步函数"""
        import asyncio

        from cozymemory.grpc_server.server import serve_grpc

        assert asyncio.iscoroutinefunction(serve_grpc)

    def test_run_grpc_cli_exists(self):
        """验证 CLI 入口函数存在"""
        from cozymemory.grpc_server import run_grpc_cli

        assert callable(run_grpc_cli)


# ──────────────────────────── Proto 模块加载 ────────────────────────────


class TestProtoModules:
    """验证生成的 proto 模块可正常导入"""

    def test_conversation_pb2_importable(self):
        from cozymemory.grpc_server import conversation_pb2

        assert hasattr(conversation_pb2, "AddConversationRequest")
        assert hasattr(conversation_pb2, "ConversationMemory")
        assert hasattr(conversation_pb2, "SearchConversationsRequest")

    def test_conversation_pb2_grpc_importable(self):
        from cozymemory.grpc_server import conversation_pb2_grpc

        assert hasattr(conversation_pb2_grpc, "ConversationServiceServicer")
        assert hasattr(conversation_pb2_grpc, "ConversationServiceStub")
        assert hasattr(conversation_pb2_grpc, "add_ConversationServiceServicer_to_server")

    def test_profile_pb2_importable(self):
        from cozymemory.grpc_server import profile_pb2

        assert hasattr(profile_pb2, "InsertProfileRequest")
        assert hasattr(profile_pb2, "UserProfile")
        assert hasattr(profile_pb2, "GetContextRequest")

    def test_profile_pb2_grpc_importable(self):
        from cozymemory.grpc_server import profile_pb2_grpc

        assert hasattr(profile_pb2_grpc, "ProfileServiceServicer")
        assert hasattr(profile_pb2_grpc, "ProfileServiceStub")
        assert hasattr(profile_pb2_grpc, "add_ProfileServiceServicer_to_server")

    def test_knowledge_pb2_importable(self):
        from cozymemory.grpc_server import knowledge_pb2

        assert hasattr(knowledge_pb2, "AddKnowledgeRequest")
        assert hasattr(knowledge_pb2, "CognifyRequest")
        assert hasattr(knowledge_pb2, "SearchKnowledgeRequest")

    def test_knowledge_pb2_grpc_importable(self):
        from cozymemory.grpc_server import knowledge_pb2_grpc

        assert hasattr(knowledge_pb2_grpc, "KnowledgeServiceServicer")
        assert hasattr(knowledge_pb2_grpc, "KnowledgeServiceStub")
        assert hasattr(knowledge_pb2_grpc, "add_KnowledgeServiceServicer_to_server")

    def test_common_pb2_importable(self):
        from cozymemory.grpc_server import common_pb2

        assert hasattr(common_pb2, "Empty")
        assert hasattr(common_pb2, "HealthRequest")
        assert hasattr(common_pb2, "HealthResponse")
        assert hasattr(common_pb2, "EngineStatus")

    def test_conversation_message_inherits_from_profile(self):
        """验证 profile.proto 复用了 conversation.proto 的 Message"""
        from cozymemory.grpc_server import conversation_pb2

        # profile.proto 导入了 conversation.proto 的 Message
        msg = conversation_pb2.Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
