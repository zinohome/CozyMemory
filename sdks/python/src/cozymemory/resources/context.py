"""Unified cross-engine context resource."""
from __future__ import annotations

from typing import Any


class _Base:
    def __init__(self, http: Any) -> None:
        self._http = http


class ContextSync(_Base):
    def get_unified(self, user_id: str, query: str | None = None) -> Any:
        """Concurrently fetch conversations + profile + knowledge context.

        Returns a dict with keys: conversations, profile_context, knowledge, errors.
        """
        body: dict[str, Any] = {"user_id": user_id}
        if query is not None:
            body["query"] = query
        return self._http.post("/api/v1/context", json=body)


class ContextAsync(_Base):
    async def get_unified(self, user_id: str, query: str | None = None) -> Any:
        body: dict[str, Any] = {"user_id": user_id}
        if query is not None:
            body["query"] = query
        return await self._http.post("/api/v1/context", json=body)
