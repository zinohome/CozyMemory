"""CozyMemory Python SDK client.

Two flavors:
  - CozyMemoryClient: sync httpx
  - CozyMemoryAsyncClient: async httpx, for FastAPI / asyncio apps

Both share the same method signatures per resource (conversations,
profiles, knowledge, context).
"""
from __future__ import annotations

from typing import Any

from ._http import AsyncHTTP, SyncHTTP
from .resources.context import ContextAsync, ContextSync
from .resources.conversations import ConversationsAsync, ConversationsSync
from .resources.knowledge import KnowledgeAsync, KnowledgeSync
from .resources.profiles import ProfilesAsync, ProfilesSync


class CozyMemoryClient:
    """Synchronous client. Suitable for scripts, WSGI apps."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self._http = SyncHTTP(api_key=api_key, base_url=base_url, timeout=timeout)
        self.conversations = ConversationsSync(self._http)
        self.profiles = ProfilesSync(self._http)
        self.knowledge = KnowledgeSync(self._http)
        self.context = ContextSync(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> CozyMemoryClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def health(self) -> Any:
        return self._http.get("/api/v1/health")


class CozyMemoryAsyncClient:
    """Async client. Use with ``async with``."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self._http = AsyncHTTP(api_key=api_key, base_url=base_url, timeout=timeout)
        self.conversations = ConversationsAsync(self._http)
        self.profiles = ProfilesAsync(self._http)
        self.knowledge = KnowledgeAsync(self._http)
        self.context = ContextAsync(self._http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> CozyMemoryAsyncClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._http.aclose()

    async def health(self) -> Any:
        return await self._http.get("/api/v1/health")
