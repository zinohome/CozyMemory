"""Conversation memory resource (Mem0-backed)."""
from __future__ import annotations

from typing import Any


class _Base:
    def __init__(self, http: Any) -> None:
        self._http = http


class ConversationsSync(_Base):
    """Synchronous conversation memory operations."""

    def add(self, user_id: str, messages: list[dict]) -> Any:
        """Add a conversation; Mem0 extracts memories. Returns server JSON."""
        return self._http.post(
            "/api/v1/conversations",
            json={"user_id": user_id, "messages": messages},
        )

    def list(self, user_id: str) -> Any:
        """List all memories for a user."""
        return self._http.get("/api/v1/conversations", params={"user_id": user_id})

    def search(self, user_id: str, query: str, limit: int = 10) -> Any:
        """Semantic search over memories."""
        return self._http.post(
            "/api/v1/conversations/search",
            json={"user_id": user_id, "query": query, "limit": limit},
        )

    def get(self, memory_id: str) -> Any:
        return self._http.get(f"/api/v1/conversations/{memory_id}")

    def delete(self, memory_id: str) -> Any:
        return self._http.delete(f"/api/v1/conversations/{memory_id}")

    def delete_all(self, user_id: str) -> Any:
        return self._http.delete(
            "/api/v1/conversations", params={"user_id": user_id}
        )


class ConversationsAsync(_Base):
    """Async conversation memory operations."""

    async def add(self, user_id: str, messages: list[dict]) -> Any:
        return await self._http.post(
            "/api/v1/conversations",
            json={"user_id": user_id, "messages": messages},
        )

    async def list(self, user_id: str) -> Any:
        return await self._http.get(
            "/api/v1/conversations", params={"user_id": user_id}
        )

    async def search(self, user_id: str, query: str, limit: int = 10) -> Any:
        return await self._http.post(
            "/api/v1/conversations/search",
            json={"user_id": user_id, "query": query, "limit": limit},
        )

    async def get(self, memory_id: str) -> Any:
        return await self._http.get(f"/api/v1/conversations/{memory_id}")

    async def delete(self, memory_id: str) -> Any:
        return await self._http.delete(f"/api/v1/conversations/{memory_id}")

    async def delete_all(self, user_id: str) -> Any:
        return await self._http.delete(
            "/api/v1/conversations", params={"user_id": user_id}
        )
