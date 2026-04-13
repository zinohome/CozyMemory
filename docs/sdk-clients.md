# CozyMemory SDK 客户端设计文档

**版本**: 2.0  
**日期**: 2026-04-13  
**状态**: 已批准

---

## 1. 设计决策

### 为什么全部自建？

| 引擎 | 官方 SDK | 能否用于自托管？ | 决策 |
|------|---------|----------------|------|
| **Cognee** | 无官方 Python SDK | — | 自建（已有代码迁移） |
| **Mem0** | `mem0ai` v1.0.11 | ❌ 不兼容自托管（端点路径、认证 Header、初始化验证） | 自建 |
| **Memobase** | `memobase` v0.0.27 | ✅ 兼容 | 自建（统一风格） |

**自建理由：**
1. Mem0 官方 SDK 与自托管服务器不兼容，必须自建
2. 三个客户端继承统一 `BaseClient`，风格一致、错误处理一致、配置一致
3. 依赖干净——只需 `httpx`，不需要安装 `mem0ai` 或 `memobase`
4. 完全控制版本和演进

---

## 2. BaseClient 设计

从现有 Cognee SDK 的 `_request` 方法提炼公共逻辑。

```python
# clients/base.py

import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EngineError(Exception):
    """引擎通信错误"""
    def __init__(self, engine: str, message: str, status_code: int | None = None):
        self.engine = engine
        self.message = message
        self.status_code = status_code
        super().__init__(f"[{engine}] {status_code} - {message}")


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
        
        # 创建 httpx 客户端
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
        headers = {"Content-Type": content_type}
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
        """
        发送 HTTP 请求，带指数退避重试。
        
        重试策略：
        - 4xx (除 429): 不重试，立即抛异常
        - 429 (限流): 重试
        - 5xx: 重试
        - 网络错误: 重试
        """
        url = f"{self.api_url}{path}"
        merged_headers = {**self._get_headers(), **(headers or {})}
        
        # 移除 Content-Type 对 multipart 请求
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
                    # 429 限流 - 重试
                    if response.status_code == 429 and attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    
                    # 4xx 客户端错误 (除 429) - 不重试
                    if 400 <= response.status_code < 500:
                        raise EngineError(
                            self.engine_name,
                            response.text or f"HTTP {response.status_code}",
                            response.status_code,
                        )
                    
                    # 5xx 服务端错误 - 重试
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    
                    raise EngineError(
                        self.engine_name,
                        response.text or f"HTTP {response.status_code}",
                        response.status_code,
                    )
                
                return response
                
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                    continue
                
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
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
```

---

## 3. Mem0Client 设计

### 3.1 自托管 Mem0 REST API 端点

| 操作 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 添加记忆 | POST | `/memories` | 传入对话消息，LLM 自动提取事实 |
| 搜索记忆 | POST | `/search` | 语义搜索 |
| 获取单条 | GET | `/memories/{id}` | 按 ID 获取 |
| 获取全部 | GET | `/memories` | 按 user_id 获取全部 |
| 更新记忆 | PUT | `/memories/{id}` | 更新记忆内容 |
| 删除单条 | DELETE | `/memories/{id}` | 按 ID 删除 |
| 删除全部 | DELETE | `/memories` | 按 user_id 删除全部 |

### 3.2 客户端实现

```python
# clients/mem0.py

from typing import Any

from .base import BaseClient, EngineError
from ..models.conversation import ConversationMemory, Message
from ..models.common import Message as CommonMessage


class Mem0Client(BaseClient):
    """Mem0 引擎客户端
    
    调用自托管 Mem0 REST API。
    注意：不使用官方 mem0ai SDK，因为其与自托管服务器不兼容。
    """
    
    def __init__(self, api_url: str = "http://localhost:8888", api_key: str | None = None, **kwargs):
        super().__init__(
            engine_name="Mem0",
            api_url=api_url,
            api_key=api_key,
            **kwargs,
        )
    
    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Mem0 自托管使用 X-API-Key 认证"""
        headers = {"Content-Type": content_type}
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
        payload: dict[str, Any] = {
            "messages": messages,
            "user_id": user_id,
            "infer": infer,
        }
        if metadata:
            payload["metadata"] = metadata
        
        response = await self._request("POST", "/memories", json=payload)
        data = response.json()
        
        # Mem0 v1.1 返回格式: [{"id": "..., "event": "ADD", "data": {"memory": "..."}}]
        results = []
        for item in data if isinstance(data, list) else [data]:
            memory_text = item.get("data", {}).get("memory", "") if isinstance(item.get("data"), dict) else item.get("memory", "")
            results.append(ConversationMemory(
                id=item.get("id", ""),
                user_id=user_id,
                content=memory_text,
                metadata=item.get("metadata"),
            ))
        return results
    
    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        threshold: float | None = None,
    ) -> list[ConversationMemory]:
        """语义搜索会话记忆"""
        payload: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "limit": limit,
        }
        if threshold is not None:
            payload["threshold"] = threshold
        
        response = await self._request("POST", "/search", json=payload)
        data = response.json()
        
        results = []
        for item in data.get("results", data if isinstance(data, list) else []):
            results.append(ConversationMemory(
                id=item.get("id", ""),
                user_id=item.get("user_id", user_id),
                content=item.get("memory", ""),
                score=item.get("score"),
                metadata=item.get("metadata"),
            ))
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
        response = await self._request(
            "GET", "/memories",
            params={"user_id": user_id, "limit": limit},
        )
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
        response = await self._request(
            "PUT", f"/memories/{memory_id}",
            json={"memory": content},
        )
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
```

---

## 4. MemobaseClient 设计

### 4.1 Memobase REST API 端点

| 操作 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 健康检查 | GET | `/healthcheck` | — |
| 创建用户 | POST | `/api/v1/users` | 返回 user_id |
| 获取用户 | GET | `/api/v1/users/{user_id}` | 返回 User 对象 |
| 删除用户 | DELETE | `/api/v1/users/{user_id}` | — |
| 插入数据 | POST | `/api/v1/blobs/insert/{user_id}` | ChatBlob 格式 |
| 触发处理 | POST | `/api/v1/users/buffer/{user_id}/chat` | flush 操作 |
| 获取画像 | GET | `/api/v1/users/profile/{user_id}` | 结构化画像 |
| 获取上下文 | GET | `/api/v1/users/context/{user_id}` | 上下文提示词 |
| 添加画像 | POST | `/api/v1/users/profile/{user_id}` | 手动添加 |
| 删除画像 | DELETE | `/api/v1/users/profile/{user_id}/{profile_id}` | 手动删除 |
| 获取事件 | GET | `/api/v1/users/event/{user_id}` | 时间线事件 |

### 4.2 客户端实现

```python
# clients/memobase.py

from typing import Any

from .base import BaseClient, EngineError
from ..models.profile import (
    ProfileTopic, UserProfile, ProfileContext,
)


class MemobaseClient(BaseClient):
    """Memobase 引擎客户端
    
    调用自托管 Memobase REST API。
    核心范式：插入对话 → flush → 获取画像/上下文。
    """
    
    def __init__(self, api_url: str = "http://localhost:8019", api_key: str = "secret", **kwargs):
        super().__init__(
            engine_name="Memobase",
            api_url=api_url,
            api_key=api_key,
            **kwargs,
        )
    
    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Memobase 使用 Bearer Token 认证"""
        headers = {"Content-Type": content_type}
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
    
    async def insert(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        sync: bool = False,
    ) -> str:
        """插入对话数据到 Memobase 缓冲区"""
        payload = {
            "messages": messages,
        }
        params = {}
        if sync:
            params["wait_process"] = "true"
        
        response = await self._request(
            "POST",
            f"/api/v1/blobs/insert/{user_id}",
            json=payload,
            params=params,
        )
        result = response.json()
        return result.get("blob_id", result.get("id", ""))
    
    async def flush(self, user_id: str, sync: bool = False) -> None:
        """触发缓冲区处理"""
        params = {}
        if sync:
            params["wait_process"] = "true"
        
        await self._request(
            "POST",
            f"/api/v1/users/buffer/{user_id}/chat",
            params=params,
        )
    
    # ===== 画像 =====
    
    async def profile(self, user_id: str) -> UserProfile:
        """获取用户结构化画像"""
        response = await self._request(
            "GET",
            f"/api/v1/users/profile/{user_id}",
            params={"need_json": "true"},
        )
        data = response.json()
        
        topics = []
        if isinstance(data, dict):
            # Memobase 返回嵌套结构: {topic: {sub_topic: {content: ..., id: ...}}}
            for topic_name, sub_topics in data.items():
                if isinstance(sub_topics, dict):
                    for sub_topic_name, content_data in sub_topics.items():
                        if isinstance(content_data, dict):
                            topics.append(ProfileTopic(
                                id=content_data.get("id", ""),
                                topic=topic_name,
                                sub_topic=sub_topic_name,
                                content=content_data.get("content", ""),
                                created_at=content_data.get("created_at"),
                                updated_at=content_data.get("updated_at"),
                            ))
        
        return UserProfile(user_id=user_id, topics=topics)
    
    async def add_profile(
        self, user_id: str, topic: str, sub_topic: str, content: str
    ) -> ProfileTopic:
        """手动添加画像条目"""
        payload = {
            "topic": topic,
            "sub_topic": sub_topic,
            "content": content,
        }
        response = await self._request(
            "POST",
            f"/api/v1/users/profile/{user_id}",
            json=payload,
        )
        result = response.json()
        return ProfileTopic(
            id=result.get("id", ""),
            topic=topic,
            sub_topic=sub_topic,
            content=content,
        )
    
    async def delete_profile(self, user_id: str, profile_id: str) -> bool:
        """删除画像条目"""
        try:
            await self._request(
                "DELETE",
                f"/api/v1/users/profile/{user_id}/{profile_id}",
            )
            return True
        except EngineError:
            return False
    
    # ===== 上下文 =====
    
    async def context(
        self,
        user_id: str,
        max_token_size: int = 500,
        chats: list[dict[str, str]] | None = None,
    ) -> ProfileContext:
        """获取上下文提示词（可直接插入 LLM prompt）"""
        params = {"max_token_size": str(max_token_size)}
        
        json_body = None
        if chats:
            json_body = {"chats": chats}
        
        response = await self._request(
            "GET",
            f"/api/v1/users/context/{user_id}",
            params=params,
            json=json_body if json_body else None,
        )
        
        # context 端点返回纯文本或 JSON
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
        response = await self._request(
            "GET",
            f"/api/v1/users/event/{user_id}",
            params={"topk": str(topk)},
        )
        data = response.json()
        return data if isinstance(data, list) else data.get("events", [])
```

---

## 5. CogneeClient 设计

从现有 `cognee_sdk` 迁移简化，核心 API 保留。

### 5.1 Cognee REST API 端点

| 操作 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 健康检查 | GET | `/health` | — |
| 添加数据 | POST | `/api/v1/add` | multipart/form-data |
| 构建图谱 | POST | `/api/v1/cognify` | 异步管道 |
| 搜索 | POST | `/api/v1/search` | 多种搜索类型 |
| 创建数据集 | POST | `/api/v1/datasets` | — |
| 列出数据集 | GET | `/api/v1/datasets` | — |
| 删除数据 | DELETE | `/api/v1/delete` | — |

### 5.2 客户端实现

```python
# clients/cognee.py

from typing import Any
from uuid import UUID

from .base import BaseClient, EngineError
from ..models.knowledge import (
    KnowledgeSearchResult, KnowledgeDataset,
)


class CogneeClient(BaseClient):
    """Cognee 引擎客户端
    
    从现有 cognee_sdk 迁移简化，保留核心 API。
    """
    
    def __init__(self, api_url: str = "http://localhost:8000", api_key: str | None = None, **kwargs):
        super().__init__(
            engine_name="Cognee",
            api_url=api_url,
            api_key=api_key,
            timeout=kwargs.pop("timeout", 300.0),  # cognify 操作需要更长超时
            **kwargs,
        )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            response = await self._request("GET", "/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def add(self, data: str, dataset: str) -> dict[str, Any]:
        """添加数据到 Cognee"""
        response = await self._request(
            "POST", "/api/v1/add",
            data={"datasetName": dataset},
            files=[("data", ("data.txt", data.encode("utf-8"), "text/plain"))],
        )
        return response.json()
    
    async def cognify(
        self,
        datasets: list[str] | None = None,
        run_in_background: bool = True,
    ) -> dict[str, Any]:
        """触发知识图谱构建"""
        payload: dict[str, Any] = {"run_in_background": run_in_background}
        if datasets:
            payload["datasets"] = datasets
        
        response = await self._request("POST", "/api/v1/cognify", json=payload)
        return response.json()
    
    async def search(
        self,
        query: str,
        dataset: str | None = None,
        search_type: str = "GRAPH_COMPLETION",
        top_k: int = 10,
    ) -> list[KnowledgeSearchResult]:
        """搜索知识库"""
        payload: dict[str, Any] = {
            "query": query,
            "search_type": search_type,
            "top_k": top_k,
        }
        if dataset:
            payload["datasets"] = [dataset]
        
        response = await self._request("POST", "/api/v1/search", json=payload)
        data = response.json()
        
        results = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict):
                results.append(KnowledgeSearchResult(**item))
        return results
    
    async def list_datasets(self) -> list[KnowledgeDataset]:
        """列出所有数据集"""
        response = await self._request("GET", "/api/v1/datasets")
        data = response.json()
        return [
            KnowledgeDataset(
                id=str(item.get("id", "")),
                name=item.get("name", ""),
                created_at=item.get("createdAt") or item.get("created_at"),
            )
            for item in data
        ]
    
    async def create_dataset(self, name: str) -> KnowledgeDataset:
        """创建数据集"""
        response = await self._request(
            "POST", "/api/v1/datasets",
            json={"name": name},
        )
        data = response.json()
        return KnowledgeDataset(
            id=str(data.get("id", "")),
            name=data.get("name", name),
            created_at=data.get("createdAt") or data.get("created_at"),
        )
    
    async def delete(self, data_id: str, dataset_id: str) -> bool:
        """删除数据"""
        try:
            await self._request(
                "DELETE", "/api/v1/delete",
                params={"data_id": data_id, "dataset_id": dataset_id},
            )
            return True
        except EngineError:
            return False
```

---

## 6. 配置管理

```python
# config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，支持环境变量和 .env 文件"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # 应用配置
    APP_NAME: str = "CozyMemory"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    GRPC_PORT: int = 50051
    
    # Mem0 引擎
    MEM0_API_URL: str = "http://localhost:8888"
    MEM0_API_KEY: str = ""
    MEM0_TIMEOUT: float = 30.0
    MEM0_ENABLED: bool = True
    
    # Memobase 引擎
    MEMOBASE_API_URL: str = "http://localhost:8019"
    MEMOBASE_API_KEY: str = "secret"
    MEMOBASE_TIMEOUT: float = 60.0
    MEMOBASE_ENABLED: bool = True
    
    # Cognee 引擎
    COGNEE_API_URL: str = "http://localhost:8000"
    COGNEE_API_KEY: str = ""
    COGNEE_TIMEOUT: float = 300.0  # cognify 操作需要更长超时
    COGNEE_ENABLED: bool = True
    
    # 日志
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"


settings = Settings()
```

---

## 7. 客户端错误处理

所有客户端错误统一为 `EngineError`，包含引擎名称和状态码：

```python
# 服务层使用示例
try:
    memories = await mem0_client.search(user_id="user_123", query="咖啡")
except EngineError as e:
    if e.status_code == 404:
        # 记忆不存在
        pass
    elif e.status_code >= 500:
        # 引擎内部错误，可重试
        logger.error(f"Mem0 服务错误: {e}")
    else:
        # 其他错误
        logger.error(f"请求失败: {e}")
```

服务层将 `EngineError` 转换为 HTTP 异常：

```python
# api/v1/conversation.py
from fastapi import HTTPException

try:
    result = await conversation_service.add(request)
except EngineError as e:
    raise HTTPException(
        status_code=502 if e.status_code and e.status_code >= 500 else 400,
        detail=f"Mem0 引擎错误: {e.message}",
    )
```