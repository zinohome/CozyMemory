"""CozyMemory gRPC 服务"""

import asyncio

import structlog

from ..logging_config import configure_logging
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

logger = structlog.get_logger()


def run_grpc_cli() -> None:
    """CLI 入口：启动 gRPC 服务器"""
    configure_logging()
    logger.info("Starting CozyMemory gRPC server...")
    asyncio.run(serve_grpc())
