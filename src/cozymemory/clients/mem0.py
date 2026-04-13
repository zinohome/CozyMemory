"""Mem0 引擎客户端

调用自托管 Mem0 REST API。
注意：不使用官方 mem0ai SDK，因为其与自托管服务器不兼容。
"""

from typing import Any

from .base import BaseClient, EngineError
from ..models.conversation import ConversationMemory


class Mem0Client(BaseClient):
    """Mem0 引擎客户端"""

    def __init__(self, api_url: str = "http://localhost:8888", api_key: str | None = None, **kwargs):
        super().__init__(engine_name="Mem0", api_url=api_url, api_key=api_key, **kwargs)

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Mem0 自托管使用 X-API-Key 认证"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False

    async def add(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
        infer: bool = True,
    ) -> list[ConversationMemory]:
        """添加对话，Mem0 自动提取事实"""
        payload: dict[str, Any] = {"messages": messages, "user_id": user_id, "infer": infer}
        if metadata:
            payload["metadata"] = metadata

        response = await self._request("POST", "/memories", json=payload)
        data = response.json()

        results = []
        for item in data if isinstance(data, list) else [data]:
            memory_text = (
                item.get("data", {}).get("memory", "") if isinstance(item.get("data"), dict) else item.get("memory", "")
            )
            results.append(
                ConversationMemory(id=item.get("id", ""), user_id=user_id, content=memory_text, metadata=item.get("metadata"))
            )
        return results

    async def search(
        self, user_id: str, query: str, limit: int = 10, threshold: float | None = None
    ) -> list[ConversationMemory]:
        """语义搜索会话记忆"""
        payload: dict[str, Any] = {"query": query, "user_id": user_id, "limit": limit}
        if threshold is not None:
            payload["threshold"] = threshold

        response = await self._request("POST", "/search", json=payload)
        data = response.json()

        results = []
        for item in data.get("results", data if isinstance(data, list) else []):
            results.append(
                ConversationMemory(
                    id=item.get("id", ""),
                    user_id=item.get("user_id", user_id),
                    content=item.get("memory", ""),
                    score=item.get("score"),
                    metadata=item.get("metadata"),
                )
            )
        return results

    async def get(self, memory_id: str) -> ConversationMemory | None:
        """获取单条记忆"""
        try:
            response = await self._request("GET", f"/memories/{memory_id}")
            item = response.json()
            return ConversationMemory(
                id=item.get("id", memory_id),
                user_id=item.get("user_id", ""),
                content=item.get("memory", ""),
                metadata=item.get("metadata"),
            )
        except EngineError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_all(self, user_id: str, limit: int = 100) -> list[ConversationMemory]:
        """获取用户所有记忆"""
        response = await self._request("GET", "/memories", params={"user_id": user_id, "limit": limit})
        data = response.json()

        items = data.get("results", data if isinstance(data, list) else [])
        return [
            ConversationMemory(
                id=item.get("id", ""),
                user_id=item.get("user_id", user_id),
                content=item.get("memory", ""),
                metadata=item.get("metadata"),
            )
            for item in items
        ]

    async def update(self, memory_id: str, content: str) -> ConversationMemory | None:
        """更新记忆内容"""
        response = await self._request("PUT", f"/memories/{memory_id}", json={"memory": content})
        item = response.json()
        return ConversationMemory(
            id=item.get("id", memory_id),
            user_id=item.get("user_id", ""),
            content=item.get("memory", content),
            metadata=item.get("metadata"),
        )

    async def delete(self, memory_id: str) -> bool:
        """删除单条记忆"""
        try:
            await self._request("DELETE", f"/memories/{memory_id}")
            return True
        except EngineError:
            return False

    async def delete_all(self, user_id: str) -> bool:
        """删除用户所有记忆"""
        try:
            await self._request("DELETE", "/memories", params={"user_id": user_id})
            return True
        except EngineError:
            return False