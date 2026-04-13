"""CozyMemory gRPC 服务"""

import asyncio
import logging

from . import (
    common_pb2,
    common_pb2_grpc,
    conversation_pb2,
    conversation_pb2_grpc,
    knowledge_pb2,
    knowledge_pb2_grpc,
    profile_pb2,
    profile_pb2_grpc,
)
from .server import (
    ConversationGrpcServicer,
    KnowledgeGrpcServicer,
    ProfileGrpcServicer,
    serve_grpc,
)

__all__ = [
    "common_pb2",
    "common_pb2_grpc",
    "conversation_pb2",
    "conversation_pb2_grpc",
    "knowledge_pb2",
    "knowledge_pb2_grpc",
    "profile_pb2",
    "profile_pb2_grpc",
    "ConversationGrpcServicer",
    "KnowledgeGrpcServicer",
    "ProfileGrpcServicer",
    "serve_grpc",
    "run_grpc_cli",
]

logger = logging.getLogger(__name__)


def run_grpc_cli() -> None:
    """CLI 入口：启动 gRPC 服务器"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting CozyMemory gRPC server...")
    asyncio.run(serve_grpc())
