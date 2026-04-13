"""BaseClient 基类

提供统一的 httpx AsyncClient 连接池管理、指数退避重试、错误处理和生命周期管理。
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class EngineError(Exception):
    """引擎通信错误"""

    def __init__(self, engine: str, message: str, status_code: int | None = None):
        self.engine = engine
        self.message = message
        self.status_code = status_code
        super().__init__(
            f"[{engine}] {status_code} - {message}" if status_code else f"[{engine}] {message}"
        )


class BaseClient:
    """
    所有引擎客户端的基类。

    提供统一的：
    - httpx AsyncClient 连接池管理
    - 指数退避重试
    - 错误处理和分类
    - 健康检查
    - 生命周期管理 (async context manager)
    """

    def __init__(
        self,
        engine_name: str,
        api_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_keepalive_connections: int = 50,
        max_connections: int = 100,
        enable_http2: bool = True,
    ):
        self.engine_name = engine_name
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections,
            ),
            follow_redirects=True,
            http2=enable_http2,
        )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """获取请求头，子类可覆盖认证方式"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: list[tuple] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """发送 HTTP 请求，带指数退避重试。

        重试策略：
        - 4xx (除 429): 不重试，立即抛异常
        - 429 (限流): 重试
        - 5xx: 重试
        - 网络错误: 重试
        """
        url = f"{self.api_url}{path}"
        merged_headers = {**self._get_headers(), **(headers or {})}

        if files:
            merged_headers.pop("Content-Type", None)

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                )

                if response.status_code >= 400:
                    if response.status_code == 429 and attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue

                    if 400 <= response.status_code < 500:
                        raise EngineError(
                            self.engine_name,
                            response.text or f"HTTP {response.status_code}",
                            response.status_code,
                        )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue

                    raise EngineError(
                        self.engine_name,
                        response.text or f"HTTP {response.status_code}",
                        response.status_code,
                    )

                return response

            except EngineError:
                raise

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue

        if last_exception:
            raise EngineError(
                self.engine_name,
                f"Request failed after {self.max_retries} attempts: {last_exception}",
            )

        raise EngineError(self.engine_name, "Request failed for unknown reason")

    async def health_check(self) -> bool:
        """健康检查，子类必须实现"""
        raise NotImplementedError

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
