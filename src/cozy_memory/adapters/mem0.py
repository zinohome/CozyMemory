"""
CozyMemory Mem0 适配器

对接 Mem0 记忆引擎，专注用户偏好和配置。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from structlog import get_logger

from ..models import Memory, MemoryCreate, MemoryQuery, MemorySource, MemoryType
from .base import BaseAdapter

logger = get_logger(__name__)


class Mem0Adapter(BaseAdapter):
    """
    Mem0 记忆适配器
    
    对接 Mem0 API，专注用户偏好、配置等记忆类型。
    
    配置:
    ```yaml
    engines:
      mem0:
        enabled: true
        api_key: "your-api-key"
        timeout: 30
    ```
    """
    
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.mem0.ai",
        timeout: int = 30,
    ):
        super().__init__(name="mem0")
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def source(self) -> MemorySource:
        return MemorySource.MEM0
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            client = self._get_client()
            response = await client.get("/v1/health")
            self._healthy = response.status_code == 200
            self._last_check = datetime.now()
            return self._healthy
        except Exception as e:
            logger.error("mem0_health_check_failed", error=str(e))
            self._healthy = False
            self._last_check = datetime.now()
            return False
    
    async def create_memory(self, memory: MemoryCreate) -> Memory:
        """创建记忆"""
        logger.info("[Mem0] 创建记忆", user_id=memory.user_id)
        
        client = self._get_client()
        
        # 调用 Mem0 API
        response = await client.post(
            "/v1/memories/",
            json={
                "user_id": memory.user_id,
                "text": memory.content,
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
            source=MemorySource.MEM0,
            metadata=memory.metadata,
            created_at=datetime.now(),
            confidence=0.9,
        )
    
    async def query_memories(self, query: MemoryQuery) -> List[Memory]:
        """查询记忆"""
        logger.info("[Mem0] 查询记忆", user_id=query.user_id)
        
        client = self._get_client()
        
        # Mem0 主要支持获取用户所有记忆
        response = await client.get(
            f"/v1/memories/{query.user_id}/",
            params={"limit": query.limit},
        )
        response.raise_for_status()
        
        data = response.json()
        memories = []
        
        for item in data:
            # 如果有查询文本，进行客户端过滤
            if query.query and query.query.lower() not in item.get("text", "").lower():
                continue
            
            memories.append(
                Memory(
                    id=item["id"],
                    user_id=query.user_id,
                    content=item.get("text", ""),
                    memory_type=MemoryType.PREFERENCE,
                    source=MemorySource.MEM0,
                    metadata=item.get("metadata"),
                    created_at=item.get("created_at"),
                    confidence=0.9,
                )
            )
        
        return memories
    
    async def update_memory(self, memory_id: str, updates: Dict[str, Any]) -> Optional[Memory]:
        """更新记忆"""
        logger.info("[Mem0] 更新记忆", memory_id=memory_id)
        
        client = self._get_client()
        
        response = await client.put(
            f"/v1/memories/{memory_id}/",
            json=updates,
        )
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        return Memory(
            id=data["id"],
            user_id=data["user_id"],
            content=data.get("text", ""),
            memory_type=MemoryType.PREFERENCE,
            source=MemorySource.MEM0,
            metadata=data.get("metadata"),
            created_at=data.get("created_at"),
            updated_at=datetime.now(),
            confidence=0.9,
        )
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        logger.info("[Mem0] 删除记忆", memory_id=memory_id)
        
        client = self._get_client()
        
        response = await client.delete(f"/v1/memories/{memory_id}/")
        
        if response.status_code == 404:
            return False
        
        response.raise_for_status()
        return True
    
    async def close(self):
        """关闭连接"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("[Mem0] 连接已关闭")
