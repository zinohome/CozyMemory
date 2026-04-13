"""Pytest 全局配置"""

import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"