"""集成测试共用 fixtures

使用说明：
  export COZY_TEST_URL=http://192.168.32.40:8000   # 真实服务地址
  pytest tests/integration/                          # 所有集成测试

若 COZY_TEST_URL 未设置，或服务无法连接，测试自动跳过。
"""

import os
import re
import uuid

import httpx
import pytest
import pytest_asyncio

# 目标服务地址：优先读环境变量，缺省本地
COZY_TEST_URL = os.getenv("COZY_TEST_URL", "http://localhost:8000").rstrip("/")
# 可选 API key：后端启用 COZY_API_KEYS 鉴权时需要
COZY_TEST_API_KEY = os.getenv("COZY_TEST_API_KEY", "cozy-dev-key-001")

_COMMON_HEADERS: dict[str, str] = (
    {"X-Cozy-API-Key": COZY_TEST_API_KEY} if COZY_TEST_API_KEY else {}
)


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
    """异步 HTTP 客户端，30s 超时，自动携带鉴权 header"""
    async with httpx.AsyncClient(
        base_url=COZY_TEST_URL, timeout=30, headers=_COMMON_HEADERS
    ) as client:
        yield client


@pytest_asyncio.fixture
async def http_slow():
    """异步 HTTP 客户端，300s 超时（用于 Cognee 全流程），自动携带鉴权 header"""
    async with httpx.AsyncClient(
        base_url=COZY_TEST_URL, timeout=300, headers=_COMMON_HEADERS
    ) as client:
        yield client


# 本次 session 里 fixture 吐出的 UUID v4 用户 id，teardown 时按此集合清理
# Redis 映射，避免留下数百条无主 UUID。
_registered_test_user_ids: set[str] = set()


@pytest.fixture
def unique_user_id() -> str:
    """每个测试生成唯一的 UUID v4 user_id（Memobase 要求），并登记以便清理"""
    uid = str(uuid.uuid4())
    _registered_test_user_ids.add(uid)
    return uid


# 识别本仓库集成/gRPC 测试制造的 dataset。合并任何一次测试运行中实际用到的命名前缀。
# 每次新增测试用例里引入新前缀时，需要同步补到这里。
_TEST_DATASET_RE = re.compile(
    r"^(grpc-(test|add|cognify|flow|crud|ctx)-|test-(ds|delete|add-timing|smoke|timing)|"
    r"smoke(-.+)?$|timing-test\d*$|integration-test-dataset$)"
)

# 识别测试制造的字符串 user_id（UUID v4 由 fixture 登记，不走正则）。
_TEST_USER_ID_RE = re.compile(
    r"^(grpc-(test|crud|ctx)-|integration-test-user$|grpc-test-user$|fresh-\d+$)"
)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_datasets():
    """测试会话结束后清理测试 dataset，避免污染 Cognee 列表。

    只在服务可达时生效；失败静默。
    只删名字匹配 _TEST_DATASET_RE 的 dataset，不会误删手工或生产数据。
    """
    yield
    if not server_is_up():
        return
    try:
        r = httpx.get(f"{COZY_TEST_URL}/api/v1/knowledge/datasets", timeout=10, headers=_COMMON_HEADERS)
        if r.status_code != 200:
            return
        datasets = r.json().get("data", [])
    except Exception:
        return
    for ds in datasets:
        name = ds.get("name", "")
        if not _TEST_DATASET_RE.match(name):
            continue
        try:
            httpx.delete(f"{COZY_TEST_URL}/api/v1/knowledge/datasets/{ds['id']}", timeout=15, headers=_COMMON_HEADERS)
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_user_mappings():
    """测试会话结束后清理 user_id → UUID 映射，避免 Redis/Users 页堆积测试遗留。

    来源：
      - UUID v4：从 _registered_test_user_ids（unique_user_id fixture 登记）
      - 字符串 id：从 /api/v1/operator/users-mapping 扫出并按 _TEST_USER_ID_RE 匹配
    """
    yield
    if not server_is_up():
        return

    to_delete: set[str] = set(_registered_test_user_ids)
    try:
        r = httpx.get(f"{COZY_TEST_URL}/api/v1/operator/users-mapping", timeout=10, headers=_COMMON_HEADERS)
        if r.status_code == 200:
            for uid in r.json().get("data", []):
                if _TEST_USER_ID_RE.match(uid):
                    to_delete.add(uid)
    except Exception:
        pass

    for uid in to_delete:
        try:
            httpx.delete(f"{COZY_TEST_URL}/api/v1/operator/users-mapping/{uid}/uuid", timeout=10, headers=_COMMON_HEADERS)
        except Exception:
            pass
