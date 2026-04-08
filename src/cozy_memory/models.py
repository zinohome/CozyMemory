"""
CozyMemory 数据模型

简洁统一的数据模型，兼容各记忆引擎。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    """记忆类型"""
    FACT = "fact"  # 事实信息
    EVENT = "event"  # 事件记录
    PREFERENCE = "preference"  # 用户偏好
    SKILL = "skill"  # 技能知识
    CONVERSATION = "conversation"  # 对话历史


class MemorySource(str, Enum):
    """记忆来源"""
    MEMOBASE = "memobase"
    MEM0 = "mem0"
    COGNEE = "cognee"
    LOCAL = "local"


class Memory(BaseModel):
    """记忆对象"""
    id: str
    user_id: str
    content: str
    memory_type: MemoryType
    source: MemorySource
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    confidence: float = Field(default=0.9, ge=0, le=1)
    
    class Config:
        use_enum_values = True


class MemoryCreate(BaseModel):
    """创建记忆请求"""
    user_id: str
    content: str
    memory_type: MemoryType = MemoryType.FACT
    metadata: Optional[Dict[str, Any]] = None


class MemoryQuery(BaseModel):
    """查询记忆请求"""
    user_id: str
    query: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    limit: int = Field(default=10, ge=1, le=100)
    engine: Optional[str] = None  # 指定引擎


class EngineConfig(BaseModel):
    """引擎配置"""
    enabled: bool = True
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 30
    priority: int = 1  # 优先级 (数字越小优先级越高)


class RouterConfig(BaseModel):
    """路由配置"""
    default_engine: str = "memobase"
    cache_ttl: int = 3600  # 缓存时间 (秒)
    cache_enabled: bool = True
    fusion_strategy: str = "rrf"  # 结果融合策略


class Config(BaseModel):
    """全局配置"""
    engines: Dict[str, EngineConfig] = Field(default_factory=dict)
    router: RouterConfig = Field(default_factory=RouterConfig)
    
    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """从 YAML 文件加载配置"""
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)
