"""
CozyMemory Memobase 适配器

对接 Memobase 记忆引擎。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from structlog import get_logger

from ..models import Memory, MemoryCreate, MemoryQuery, MemorySource, MemoryType
from .base import BaseAdapter

logger = get_logger(__name__)


class MemobaseAdapter(BaseAdapter):
    """
    Memobase 记忆适配器
    
    对接 Memobase API，支持事实、事件、技能等记忆类型。
    
    配置:
    ```yaml
    engines:
      memobase:
        enabled: true
        api_url: "http://localhost:8000"
        timeout: 30
    ```
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        timeout: int = 30,
    ):
        super().__init__(name="memobase")
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def source(self) -> MemorySource:
        return MemorySource.MEMOBASE
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            client = self._get_client()
            response = await client.get("/health")
            self._healthy = response.status_code == 200
            self._last_check = datetime.now()
            return self._healthy
        except Exception as e:
            logger.error("memobase_health_check_failed", error=str(e))
            self._healthy = False
            self._last_check = datetime.now()
            return False
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆"""
        logger.info("[Memobase] 创建记忆", user_id=memory.user_id)
        
        client = self._get_client()
        
        # 调用 Memobase API
        response = await client.post(
            "/api/v1/memories",
            json={
                "user_id": memory.user_id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "metadata": memory.metadata,
            },
        )
        response.raise_for_status()
        
        data = response.json()
        
        return Memory(
            id=data.get("id", f"mem_{datetime.now().timestamp()}"),
            user_id=memory.user_id,
            content=memory.content,
            memory_type=memory.memory_type,
            source=MemorySource.MEMOBASE,
            metadata=memory.metadata,
            created_at=datetime.now(),
            confidence=0.9,
        )
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """查询记忆"""
        logger.info("[Memobase] 查询记忆", user_id=query.user_id, query=query.query)
        
        client = self._get_client()
        
        # 构建查询参数
        params = {
            "user_id": query.user_id,
            "limit": query.limit,
        }
        
        if query.query:
            params["q"] = query.query
        
        if query.memory_type:
            params["type"] = query.memory_type.value
        
        # 调用 API
        response = await client.get("/api/v1/memories", params=params)
        response.raise_for_status()
        
        data = response.json()
        memories = []
        
        for item in data.get("items", []):
            memories.append(
                Memory(
                    id=item["id"],
                    user_id=item["user_id"],
                    content=item["content"],
                    memory_type=MemoryType(item["memory_type"]),
                    source=MemorySource.MEMOBASE,
                    metadata=item.get("metadata"),
                    created_at=item.get("created_at"),
                    confidence=item.get("confidence", 0.9),
                )
            )
        
        return memories
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        """更新记忆"""
        logger.info("[Memobase] 更新记忆", memory_id=memory_id)
        
        client = self._get_client()
        
        response = await client.put(
            f"/api/v1/memories/{memory_id}",
            json=updates,
        )
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        return Memory(
            id=data["id"],
            user_id=data["user_id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            source=MemorySource.MEMOBASE,
            metadata=data.get("metadata"),
            created_at=data.get("created_at"),
            updated_at=datetime.now(),
            confidence=data.get("confidence", 0.9),
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        logger.info("[Memobase] 删除记忆", memory_id=memory_id)
        
        client = self._get_client()
        
        response = await client.delete(f"/api/v1/memories/{memory_id}")
        
        if response.status_code == 404:
            return False
        
        response.raise_for_status()
        return True
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("[Memobase] 连接已关闭")
