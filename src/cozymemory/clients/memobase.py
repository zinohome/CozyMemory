"""Memobase 引擎客户端

调用自托管 Memobase REST API。
核心范式：插入对话 → flush → 获取画像/上下文。
"""

from typing import Any

from ..models.profile import ProfileContext, ProfileTopic, UserProfile
from .base import BaseClient, EngineError


class MemobaseClient(BaseClient):
    """Memobase 引擎客户端"""

    def __init__(
        self, api_url: str = "http://localhost:8019", api_key: str = "secret", **kwargs: Any
    ) -> None:
        super().__init__(engine_name="Memobase", api_url=api_url, api_key=api_key, **kwargs)

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Memobase 使用 Bearer Token 认证"""
        headers: dict[str, str] = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def health_check(self) -> bool:
        """健康检查 — Memobase 健康端点为 /api/v1/healthcheck"""
        try:
            response = await self._request("GET", "/api/v1/healthcheck")
            return response.status_code == 200
        except Exception:
            return False

    # ===== 用户管理 =====

    async def add_user(self, user_id: str | None = None, data: dict[str, Any] | None = None) -> str:
        """创建用户，返回 user_id。若用户已存在则静默忽略 (upsert 语义)。

        注意：Memobase 用 HTTP 200 + errno 字段表达业务错误，不使用 HTTP 4xx/5xx。
        """
        payload: dict[str, Any] = {}
        if user_id:
            payload["id"] = user_id
        if data:
            payload["data"] = data
        response = await self._request("POST", "/api/v1/users", json=payload)
        result: dict[str, Any] = response.json()
        # UniqueViolation = user already exists, treat as success
        if result.get("errno", 0) != 0 and "UniqueViolation" not in result.get("errmsg", ""):
            raise EngineError(self.engine_name, result.get("errmsg", "Unknown error"), 500)
        data_field = result.get("data") or {}
        return str(data_field.get("id", user_id or ""))

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """获取用户信息"""
        response = await self._request("GET", f"/api/v1/users/{user_id}")
        return dict(response.json())

    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            await self._request("DELETE", f"/api/v1/users/{user_id}")
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise

    # ===== 数据插入 =====

    async def insert(self, user_id: str, messages: list[dict[str, str]], sync: bool = False) -> str:
        """插入对话数据到 Memobase 缓冲区。若用户不存在则自动创建。

        Memobase API 格式：{"blob_type": "chat", "blob_data": {"messages": [...]}}
        """
        payload: dict[str, Any] = {
            "blob_type": "chat",
            "blob_data": {"messages": messages},
        }
        params: dict[str, str] = {}
        if sync:
            params["wait_process"] = "true"

        response = await self._request(
            "POST", f"/api/v1/blobs/insert/{user_id}", json=payload, params=params
        )
        result: dict[str, Any] = response.json()

        if result.get("errno", 0) != 0:
            if "ForeignKeyViolation" in result.get("errmsg", ""):
                # 用户不存在，自动创建后重试
                await self.add_user(user_id=user_id)
                response = await self._request(
                    "POST", f"/api/v1/blobs/insert/{user_id}", json=payload, params=params
                )
                result = response.json()
                if result.get("errno", 0) != 0:
                    raise EngineError(self.engine_name, result.get("errmsg", "Unknown error"), 500)
            else:
                raise EngineError(self.engine_name, result.get("errmsg", "Unknown error"), 500)

        # 响应格式：{"data": {"id": "<blob_id>", "chat_results": [...]}, "errno": 0}
        data = result.get("data") or {}
        return str(data.get("id", data.get("blob_id", "")))

    async def flush(self, user_id: str, sync: bool = False) -> None:
        """触发缓冲区处理"""
        params = {}
        if sync:
            params["wait_process"] = "true"
        await self._request("POST", f"/api/v1/users/buffer/{user_id}/chat", params=params)

    # ===== 画像 =====

    async def profile(self, user_id: str) -> UserProfile:
        """获取用户结构化画像

        Memobase 响应格式：{"data": {"profiles": [{"id": ..., "content": ...,
        "attributes": {"topic": ..., "sub_topic": ...}}]}, "errno": 0}
        """
        response = await self._request(
            "GET", f"/api/v1/users/profile/{user_id}", params={"need_json": "true"}
        )
        raw = response.json()

        # 兼容新旧两种格式
        if isinstance(raw, dict) and "data" in raw:
            profiles_list = raw["data"].get("profiles", [])
            topics = [
                ProfileTopic(
                    id=item.get("id", ""),
                    topic=item.get("attributes", {}).get("topic", ""),
                    sub_topic=item.get("attributes", {}).get("sub_topic", ""),
                    content=item.get("content", ""),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                )
                for item in profiles_list
                if isinstance(item, dict)
            ]
        else:
            # 旧格式兼容：{topic: {sub_topic: {id, content, ...}}}
            topics = []
            if isinstance(raw, dict):
                for topic_name, sub_topics in raw.items():
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

    async def add_profile(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> ProfileTopic:
        """手动添加画像条目"""
        payload = {"topic": topic, "sub_topic": sub_topic, "content": content}
        response = await self._request("POST", f"/api/v1/users/profile/{user_id}", json=payload)
        result = response.json()
        if isinstance(result, dict) and result.get("errno", 0) != 0:
            raise EngineError(self.engine_name, result.get("errmsg", "add_profile failed"), 500)
        data = result.get("data", result) if isinstance(result, dict) else {}
        return ProfileTopic(
            id=data.get("id", ""),
            topic=topic,
            sub_topic=sub_topic,
            content=content,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    async def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """删除画像条目"""
        try:
            await self._request("DELETE", f"/api/v1/users/profile/{user_id}/{profile_id}")
            return True
        except EngineError as e:
            if e.status_code == 404:
                return True  # 幂等：不存在视为已删除
            raise

    # ===== 上下文 =====

    async def context(
        self, user_id: str, max_token_size: int = 500, chats: list[dict[str, str]] | None = None
    ) -> ProfileContext:
        """获取上下文提示词（可直接插入 LLM prompt）"""
        params = {"max_token_size": str(max_token_size)}
        # Note: Memobase context endpoint is GET-only; the optional `chats` parameter
        # cannot be sent as a request body on GET requests and is currently unused.
        response = await self._request(
            "GET",
            f"/api/v1/users/context/{user_id}",
            params=params,
        )

        body = response.json()
        # 响应格式：{"data": {"context": "..."}, "errno": 0, "errmsg": ""}
        if isinstance(body, dict) and "data" in body:
            inner = body.get("data") or {}
            context_text = inner.get("context", inner.get("result", ""))
        elif isinstance(body, dict):
            context_text = body.get("context", body.get("result", str(body)))
        else:
            context_text = str(body)

        return ProfileContext(user_id=user_id, context=context_text)

