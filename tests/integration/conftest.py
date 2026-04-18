"""集成测试共用 fixtures

使用说明：
  export COZY_TEST_URL=http://192.168.32.40:8000   # 真实服务地址
  pytest tests/integration/                          # 所有集成测试

若 COZY_TEST_URL 未设置，或服务无法连接，测试自动跳过。
"""

import os
import uuid

import httpx
import pytest
import pytest_asyncio

# 目标服务地址：优先读环境变量，缺省本地
COZY_TEST_URL = os.getenv("COZY_TEST_URL", "http://localhost:8000").rstrip("/")


def _server_reachable() -> bool:
    """同步探测：health 端点是否可达"""
    try:
        r = httpx.get(f"{COZY_TEST_URL}/api/v1/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# 模块级别只探测一次，避免每个测试都发请求
_server_up: bool | None = None


def server_is_up() -> bool:
    global _server_up
    if _server_up is None:
        _server_up = _server_reachable()
    return _server_up


requires_server = pytest.mark.skipif(
    not server_is_up(),
    reason=f"CozyMemory server not reachable at {COZY_TEST_URL}",
)


@pytest_asyncio.fixture
async def http():
    """异步 HTTP 客户端，30s 超时"""
    async with httpx.AsyncClient(base_url=COZY_TEST_URL, timeout=30) as client:
        yield client


@pytest_asyncio.fixture
async def http_slow():
    """异步 HTTP 客户端，300s 超时（用于 Cognee 全流程）"""
    async with httpx.AsyncClient(base_url=COZY_TEST_URL, timeout=300) as client:
        yield client


@pytest.fixture
def unique_user_id() -> str:
    """每个测试生成唯一的 UUID v4 user_id（Memobase 要求）"""
    return str(uuid.uuid4())
