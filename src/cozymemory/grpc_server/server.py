"""gRPC 服务器

启动 gRPC 服务，复用 Service 层逻辑。
gRPC 功能在 REST API 完成后再实现。
"""

import logging
from concurrent import futures

import grpc

from ..config import settings

logger = logging.getLogger(__name__)


async def serve_grpc():
    """启动 gRPC 服务器（占位实现）"""
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    # TODO: 注册 gRPC 服务实现
    server.add_insecure_port(f"[::]:{settings.GRPC_PORT}")
    await server.start()
    logger.info(f"gRPC server started on port {settings.GRPC_PORT}")
    await server.wait_for_termination()
