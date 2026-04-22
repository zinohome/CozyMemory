"""SQLAlchemy 2.0 async engine + session factory。

应用启动时 init_engine()，结束时 close_engine()。
请求处理中通过 FastAPI Depends(get_session) 拿会话。
"""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..config import settings

logger = structlog.get_logger()

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    """创建全局 engine / session factory。幂等，多次调用只初始化一次。"""
    global _engine, _session_factory
    if _engine is not None:
        return
    _engine = create_async_engine(
        settings.DATABASE_URL,
        # SQL 日志：DEBUG 模式打开方便排错
        echo=settings.DEBUG,
        # asyncpg 连接池：默认 5；这里调到 10 覆盖 API 并发
        pool_size=10,
        max_overflow=5,
        # 每个连接用满 1h 回收，防 PG 服务端超时关连接
        pool_recycle=3600,
        # 预检查连接是否健康，避免拿到已关闭的连接
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("db.init", url=settings.DATABASE_URL.split("@")[-1])


async def close_engine() -> None:
    """应用 shutdown 时调，优雅关闭连接池。"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("db.close")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 注入的 session 生成器。每个请求一个 session，自动关闭。"""
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
