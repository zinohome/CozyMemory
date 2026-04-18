"""structlog 结构化日志配置

development 模式：彩色可读格式（ConsoleRenderer）
production  模式：JSON 格式（适合 ELK/Loki 日志收集）

用法：
    from cozymemory.logging_config import configure_logging
    configure_logging(env="development", level="INFO")

日志调用：
    import structlog
    logger = structlog.get_logger()
    logger.info("event", user_id="u1", duration_ms=42)

请求上下文绑定（在中间件中）：
    structlog.contextvars.bind_contextvars(request_id="abc", path="/api/v1/health")
    # 之后同一协程的所有日志自动携带这些字段
    structlog.contextvars.clear_contextvars()
"""

import logging
import sys
from typing import Any

import structlog


def configure_logging(env: str = "development", level: str = "INFO") -> None:
    """初始化 structlog 和 stdlib logging。

    Args:
        env:   运行环境，"development" 或 "production"
        level: 日志级别，如 "DEBUG"、"INFO"、"WARNING"
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 所有环境共用的处理器链
    shared_processors: list[Any] = [
        # 合并 contextvars（request_id / method / path 等请求上下文）
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if env == "production":
        # JSON 格式：每行一个 JSON 对象，适合机器解析
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        # 彩色可读格式：适合本地终端
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.processors.format_exc_info,
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # stdlib logging：让 uvicorn/grpcio/httpx 等第三方库的日志也能输出
    # 保持简单格式，不和 structlog 混用渲染器
    logging.basicConfig(
        format="%(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    # 降低高频第三方库的日志噪音
    for noisy_logger in ("httpx", "httpcore", "grpc", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
