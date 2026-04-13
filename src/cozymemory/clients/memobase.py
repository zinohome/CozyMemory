"""Memobase 引擎客户端

调用自托管 Memobase REST API。
核心范式：插入对话 → flush → 获取画像/上下文。
"""

from typing import Any

from .base import BaseClient, EngineError
from ..models.profile import ProfileTopic, UserProfile, ProfileContext


class MemobaseClient(BaseClient):
    """Memobase 引擎客户端"""

    def __init__(self, api_url: str = "http://localhost:8019", api_key: str = "secret", **kwargs):
        super().__init__(engine_name="Memobase", api_url=api_url, api_key=api_key, **kwargs)

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Memobase 使用 Bearer Token 认证"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/healthcheck")
            return response.status_code == 200
        except Exception:
            return False

    # ===== 用户管理 =====

    async def add_user(self, user_id: str | None = None, data: dict | None = None) -> str:
        """创建用户，返回 user_id"""
        payload: dict[str, Any] = {}
        if user_id:
            payload["id"] = user_id
        if data:
            payload["data"] = data
        response = await self._request("POST", "/api/v1/users", json=payload)
        result = response.json()
        return result.get("id", result.get("user_id", ""))

    async def get_user(self, user_id: str) -> dict:
        """获取用户信息"""
        response = await self._request("GET", f"/api/v1/users/{user_id}")
        return response.json()

    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            await self._request("DELETE", f"/api/v1/users/{user_id}")
            return True
        except EngineError:
            return False

    # ===== 数据插入 =====

    async def insert(self, user_id: str, messages: list[dict[str, str]], sync: bool = False) -> str:
        """插入对话数据到 Memobase 缓冲区"""
        payload = {"messages": messages}
        params = {}
        if sync:
            params["wait_process"] = "true"
        response = await self._request("POST", f"/api/v1/blobs/insert/{user_id}", json=payload, params=params)
        result = response.json()
        return result.get("blob_id", result.get("id", ""))

    async def flush(self, user_id: str, sync: bool = False) -> None:
        """触发缓冲区处理"""
        params = {}
        if sync:
            params["wait_process"] = "true"
        await self._request("POST", f"/api/v1/users/buffer/{user_id}/chat", params=params)

    # ===== 画像 =====

    async def profile(self, user_id: str) -> UserProfile:
        """获取用户结构化画像"""
        response = await self._request("GET", f"/api/v1/users/profile/{user_id}", params={"need_json": "true"})
        data = response.json()

        topics = []
        if isinstance(data, dict):
            for topic_name, sub_topics in data.items():
                if isinstance(sub_topics, dict):
                    for sub_topic_name, content_data in sub_topics.items():
                        if isinstance(content_data, dict):
                            topics.append(
                                ProfileTopic(
                                    id=content_data.get("id", ""),
                                    topic=topic_name,
                                    sub_topic=sub_topic_name,
                                    content=content_data.get("content", ""),
                                    created_at=content_data.get("created_at"),
                                    updated_at=content_data.get("updated_at"),
                                )
                            )
        return UserProfile(user_id=user_id, topics=topics)

    async def add_profile(self, user_id: str, topic: str, sub_topic: str, content: str) -> ProfileTopic:
        """手动添加画像条目"""
        payload = {"topic": topic, "sub_topic": sub_topic, "content": content}
        response = await self._request("POST", f"/api/v1/users/profile/{user_id}", json=payload)
        result = response.json()
        return ProfileTopic(id=result.get("id", ""), topic=topic, sub_topic=sub_topic, content=content)

    async def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """删除画像条目"""
        try:
            await self._request("DELETE", f"/api/v1/users/profile/{user_id}/{profile_id}")
            return True
        except EngineError:
            return False

    # ===== 上下文 =====

    async def context(self, user_id: str, max_token_size: int = 500, chats: list[dict[str, str]] | None = None) -> ProfileContext:
        """获取上下文提示词（可直接插入 LLM prompt）"""
        params = {"max_token_size": str(max_token_size)}
        json_body = None
        if chats:
            json_body = {"chats": chats}

        response = await self._request(
            "GET", f"/api/v1/users/context/{user_id}", params=params, json=json_body if json_body else None
        )

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            context_text = data.get("context", data.get("result", str(data)))
        else:
            context_text = response.text

        return ProfileContext(user_id=user_id, context=context_text)

    # ===== 事件 =====

    async def events(self, user_id: str, topk: int = 10) -> list[dict]:
        """获取用户事件时间线"""
        response = await self._request("GET", f"/api/v1/users/event/{user_id}", params={"topk": str(topk)})
        data = response.json()
        return data if isinstance(data, list) else data.get("events", [])