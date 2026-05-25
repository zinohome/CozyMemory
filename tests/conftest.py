"""Pytest 全局配置"""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def restore_settings():
    """测试间隔离：保存并在每次测试后恢复 settings 中被测试直接赋值的字段。

    多个单元测试 fixture 会直接修改 settings 单例（如 COZY_API_KEYS、DATABASE_URL），
    但没有在 yield 后还原。不还原会污染同进程后续测试。
    """
    from cozymemory.config import settings

    saved = {
        "COZY_API_KEYS": settings.COZY_API_KEYS,
        "DATABASE_URL": settings.DATABASE_URL,
    }
    yield
    for key, value in saved.items():
        setattr(settings, key, value)
