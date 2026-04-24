"""User-profile resource (Memobase-backed)."""
from __future__ import annotations

from typing import Any


class _Base:
    def __init__(self, http: Any) -> None:
        self._http = http


class ProfilesSync(_Base):
    def insert(self, user_id: str, messages: list[dict], sync: bool = False) -> Any:
        """Push a chat blob for profile extraction.

        NOTE: user_id must be a UUID v4 — Memobase enforces this.
        """
        return self._http.post(
            "/api/v1/profiles/insert",
            json={"user_id": user_id, "messages": messages, "sync": sync},
        )

    def flush(self, user_id: str) -> Any:
        return self._http.post("/api/v1/profiles/flush", json={"user_id": user_id})

    def get(self, user_id: str) -> Any:
        return self._http.get(f"/api/v1/profiles/{user_id}")

    def get_context(self, user_id: str, max_token_size: int | None = None) -> Any:
        body: dict[str, Any] = {}
        if max_token_size is not None:
            body["max_token_size"] = max_token_size
        return self._http.post(f"/api/v1/profiles/{user_id}/context", json=body)

    def add_item(self, user_id: str, topic: str, sub_topic: str, content: str) -> Any:
        return self._http.post(
            f"/api/v1/profiles/{user_id}/items",
            json={"topic": topic, "sub_topic": sub_topic, "content": content},
        )

    def delete_item(self, user_id: str, profile_id: str) -> Any:
        return self._http.delete(f"/api/v1/profiles/{user_id}/items/{profile_id}")


class ProfilesAsync(_Base):
    async def insert(
        self, user_id: str, messages: list[dict], sync: bool = False
    ) -> Any:
        return await self._http.post(
            "/api/v1/profiles/insert",
            json={"user_id": user_id, "messages": messages, "sync": sync},
        )

    async def flush(self, user_id: str) -> Any:
        return await self._http.post(
            "/api/v1/profiles/flush", json={"user_id": user_id}
        )

    async def get(self, user_id: str) -> Any:
        return await self._http.get(f"/api/v1/profiles/{user_id}")

    async def get_context(
        self, user_id: str, max_token_size: int | None = None
    ) -> Any:
        body: dict[str, Any] = {}
        if max_token_size is not None:
            body["max_token_size"] = max_token_size
        return await self._http.post(
            f"/api/v1/profiles/{user_id}/context", json=body
        )

    async def add_item(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> Any:
        return await self._http.post(
            f"/api/v1/profiles/{user_id}/items",
            json={"topic": topic, "sub_topic": sub_topic, "content": content},
        )

    async def delete_item(self, user_id: str, profile_id: str) -> Any:
        return await self._http.delete(
            f"/api/v1/profiles/{user_id}/items/{profile_id}"
        )
