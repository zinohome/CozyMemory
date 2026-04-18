"""BaseClient 基类测试"""

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cozymemory.clients.base import BaseClient, EngineError


def test_engine_error_creation():
    """EngineError 正确创建"""
    err = EngineError("Mem0", "服务不可用", 503)
    assert err.engine == "Mem0"
    assert err.message == "服务不可用"
    assert err.status_code == 503
    assert "[Mem0]" in str(err)


def test_engine_error_no_status():
    """EngineError 无状态码"""
    err = EngineError("Cognee", "连接超时")
    assert err.status_code is None


def test_base_client_init():
    """BaseClient 正确初始化"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    assert client.engine_name == "Test"
    assert client.api_url == "http://localhost:8000"
    assert client.max_retries == 3
    assert client.retry_delay == 1.0


def test_base_client_url_trailing_slash():
    """BaseClient 去除 URL 尾部斜杠"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000/")
    assert client.api_url == "http://localhost:8000"


def test_base_client_headers_with_key():
    """BaseClient 带 API Key 的请求头"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", api_key="my-key")
    headers = client._get_headers()
    assert headers["Authorization"] == "Bearer my-key"
    assert headers["Content-Type"] == "application/json"


def test_base_client_headers_without_key():
    """BaseClient 无 API Key 的请求头"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    headers = client._get_headers()
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_base_client_request_success():
    """BaseClient 成功请求"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    mock_response = httpx.Response(200, json={"status": "ok"})
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        response = await client._request("GET", "/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_base_client_request_4xx_no_retry():
    """BaseClient 4xx 错误不重试"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000", max_retries=3)
    mock_response = httpx.Response(400, text="Bad Request")
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ):
        with pytest.raises(EngineError) as exc_info:
            await client._request("GET", "/bad")
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_base_client_request_5xx_retry():
    """BaseClient 5xx 错误重试后抛异常"""
    client = BaseClient(
        engine_name="Test", api_url="http://localhost:8000", max_retries=2, retry_delay=0.01
    )
    mock_response = httpx.Response(500, text="Internal Server Error")
    with patch.object(
        client._client, "request", new_callable=AsyncMock, return_value=mock_response
    ) as mock_req:
        with pytest.raises(EngineError) as exc_info:
            await client._request("GET", "/error")
        assert exc_info.value.status_code == 500
        assert mock_req.call_count == 2


@pytest.mark.asyncio
async def test_base_client_request_timeout_retry():
    """BaseClient 超时错误重试"""
    client = BaseClient(
        engine_name="Test", api_url="http://localhost:8000", max_retries=2, retry_delay=0.01
    )
    with patch.object(
        client._client,
        "request",
        new_callable=AsyncMock,
        side_effect=httpx.TimeoutException("timeout"),
    ) as mock_req:
        with pytest.raises(EngineError):
            await client._request("GET", "/slow")
        assert mock_req.call_count == 2


@pytest.mark.asyncio
async def test_base_client_health_check_not_implemented():
    """BaseClient 健康检查未实现"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with pytest.raises(NotImplementedError):
        await client.health_check()


@pytest.mark.asyncio
async def test_base_client_close():
    """BaseClient 关闭连接"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with patch.object(client._client, "aclose", new_callable=AsyncMock):
        await client.close()


@pytest.mark.asyncio
async def test_base_client_context_manager():
    """BaseClient 异步上下文管理器"""
    client = BaseClient(engine_name="Test", api_url="http://localhost:8000")
    with patch.object(client._client, "aclose", new_callable=AsyncMock):
        async with client as c:
            assert c is client


# ===== Circuit Breaker =====


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """连续 5xx 失败达到阈值后熔断器打开，后续请求快速失败"""
    client = BaseClient(
        engine_name="Test",
        api_url="http://localhost:8000",
        max_retries=1,
        retry_delay=0.0,
        failure_threshold=3,
        circuit_recovery_timeout=60.0,
    )
    mock_500 = httpx.Response(500, text="error")
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_500):
        # 3 consecutive 5xx failures — should open the circuit
        for _ in range(3):
            with pytest.raises(EngineError):
                await client._request("GET", "/fail")

    assert client._consecutive_failures >= 3
    assert client._circuit_open_until > time.monotonic()

    # Next call should fail-fast without hitting the backend
    with patch.object(client._client, "request", new_callable=AsyncMock) as mock_req:
        with pytest.raises(EngineError) as exc_info:
            await client._request("GET", "/fail")
        mock_req.assert_not_called()
        assert "circuit open" in exc_info.value.message


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success():
    """成功请求后连续失败计数清零"""
    client = BaseClient(
        engine_name="Test",
        api_url="http://localhost:8000",
        max_retries=1,
        retry_delay=0.0,
        failure_threshold=5,
    )
    client._consecutive_failures = 4  # one below threshold

    mock_ok = httpx.Response(200, json={"ok": True})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_ok):
        await client._request("GET", "/ok")

    assert client._consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_4xx_does_not_count():
    """4xx 客户端错误不计入熔断器失败计数"""
    client = BaseClient(
        engine_name="Test",
        api_url="http://localhost:8000",
        max_retries=1,
        retry_delay=0.0,
        failure_threshold=3,
    )
    mock_400 = httpx.Response(400, text="bad request")
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_400):
        for _ in range(5):
            with pytest.raises(EngineError):
                await client._request("GET", "/bad")

    # circuit should still be closed — 4xx errors don't count
    assert client._circuit_open_until <= time.monotonic()


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_probe():
    """熔断器恢复窗口过后允许一次探测请求"""
    client = BaseClient(
        engine_name="Test",
        api_url="http://localhost:8000",
        max_retries=1,
        retry_delay=0.0,
        failure_threshold=3,
        circuit_recovery_timeout=60.0,
    )
    # Manually set circuit open state but with expired timeout
    client._consecutive_failures = 3
    client._circuit_open_until = time.monotonic() - 1.0  # already expired

    mock_ok = httpx.Response(200, json={"ok": True})
    with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_ok):
        # Probe should be allowed through
        await client._request("GET", "/probe")

    assert client._consecutive_failures == 0  # reset after success
