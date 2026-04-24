"""BaseClient 基类

提供统一的 httpx AsyncClient 连接池管理、指数退避重试、错误处理和生命周期管理。
"""

import asyncio
import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


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
        failure_threshold: int = 5,
        circuit_recovery_timeout: float = 60.0,
    ):
        self.engine_name = engine_name
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._failure_threshold = failure_threshold
        self._circuit_recovery_timeout = circuit_recovery_timeout
        self._consecutive_failures: int = 0
        self._circuit_open_until: float = 0.0

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=max_keepalive_connections,
                max_connections=max_connections,
            ),
            follow_redirects=True,
            http2=enable_http2,
        )

    # ── Circuit breaker helpers ──────────────────────────────────────────

    def _is_circuit_open(self) -> bool:
        """如果熔断器打开且未到恢复时间，返回 True（快速失败）。
        到达恢复时间后允许一次探测请求（半开状态）。
        """
        if self._consecutive_failures >= self._failure_threshold:
            if time.monotonic() < self._circuit_open_until:
                return True
            # 半开：允许一次探测，降低计数使下次失败能重新触发
            self._consecutive_failures = self._failure_threshold - 1
        return False

    def _record_success(self) -> None:
        """请求成功：重置连续失败计数。"""
        self._consecutive_failures = 0

    def _record_transient_failure(self) -> None:
        """瞬态失败（5xx / 网络错误）：累计计数，达到阈值则打开熔断器。"""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._circuit_open_until = time.monotonic() + self._circuit_recovery_timeout
            logger.warning(
                "circuit_breaker.open",
                engine=self.engine_name,
                failures=self._consecutive_failures,
                recovery_in=self._circuit_recovery_timeout,
            )

    # ────────────────────────────────────────────────────────────────────

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
        files: list[tuple[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """发送 HTTP 请求，带指数退避重试。

        重试策略：
        - 4xx (除 429): 不重试，立即抛异常
        - 429 (限流): 重试
        - 5xx: 重试
        - 网络错误: 重试
        """
        if self._is_circuit_open():
            raise EngineError(
                self.engine_name,
                f"circuit open: upstream unavailable, retry in "
                f"{self._circuit_open_until - time.monotonic():.0f}s",
            )

        from ..metrics import engine_request_duration, engine_request_errors

        url = f"{self.api_url}{path}"
        merged_headers = {**self._get_headers(), **(headers or {})}

        if files:
            merged_headers.pop("Content-Type", None)

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                _t0 = time.monotonic()
                response = await self._client.request(
                    method=method,
                    url=url,
                    headers=merged_headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                )
                engine_request_duration.labels(
                    engine=self.engine_name, method=method, path=path,
                ).observe(time.monotonic() - _t0)

                if response.status_code >= 400:
                    if response.status_code == 429 and attempt < self.max_retries - 1:
                        logger.warning(
                            "engine.retry",
                            engine=self.engine_name,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            status=429,
                            reason="rate_limited",
                        )
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue

                    if 400 <= response.status_code < 500:
                        raise EngineError(
                            self.engine_name,
                            response.text or f"HTTP {response.status_code}",
                            response.status_code,
                        )

                    if attempt < self.max_retries - 1:
                        logger.warning(
                            "engine.retry",
                            engine=self.engine_name,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            status=response.status_code,
                            reason="server_error",
                        )
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue

                    self._record_transient_failure()
                    raise EngineError(
                        self.engine_name,
                        response.text or f"HTTP {response.status_code}",
                        response.status_code,
                    )

                self._record_success()
                return response

            except EngineError:
                raise

            except httpx.TimeoutException as e:
                engine_request_errors.labels(engine=self.engine_name, error_type="timeout").inc()
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "engine.retry",
                        engine=self.engine_name,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        reason="timeout",
                        error=str(e),
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue

            except httpx.RequestError as e:
                engine_request_errors.labels(engine=self.engine_name, error_type="network").inc()
                last_exception = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "engine.retry",
                        engine=self.engine_name,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        reason="network_error",
                        error=str(e),
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue

        if last_exception:
            self._record_transient_failure()
            raise EngineError(
                self.engine_name,
                f"Request failed after {self.max_retries} attempts: {last_exception}",
            )

        self._record_transient_failure()
        raise EngineError(self.engine_name, "Request failed for unknown reason")

    async def health_check(self) -> bool:
        """健康检查，子类必须实现"""
        raise NotImplementedError

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        await self._client.aclose()

    async def __aenter__(self) -> "BaseClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        await self.close()
