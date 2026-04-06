"""
数据模型模块

定义记忆相关的 Pydantic 模型，用于 API 请求/响应验证。
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型"""
    FACT = "fact"  # 事实记忆
    EVENT = "event"  # 事件记忆
    PREFERENCE = "preference"  # 偏好记忆
    SKILL = "skill"  # 技能记忆
    CONVERSATION = "conversation"  # 对话记忆


class MemorySource(str, Enum):
    """记忆来源"""
    MEMOBASE = "memobase"
    MEM0 = "mem0"
    COGNEE = "cognee"
    USER_INPUT = "user_input"


# ==================== 请求模型 ====================

class MemoryCreate(BaseModel):
    """创建记忆请求"""
    
    user_id: str = Field(..., description="用户 ID", min_length=1)
    content: str = Field(..., description="记忆内容", min_length=1)
    memory_type: MemoryType = Field(
        default=MemoryType.FACT,
        description="记忆类型"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="元数据"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "content": "用户喜欢喝拿铁咖啡",
                "memory_type": "preference",
                "metadata": {"source": "chat", "confidence": 0.95}
            }
        }


class MemoryQuery(BaseModel):
    """查询记忆请求"""
    
    user_id: str = Field(..., description="用户 ID", min_length=1)
    query: Optional[str] = Field(
        default=None,
        description="查询文本 (可选，用于语义搜索)"
    )
    memory_type: Optional[MemoryType] = Field(
        default=None,
        description="记忆类型过滤"
    )
    limit: int = Field(default=10, ge=1, le=100, description="返回数量限制")
    engine: Optional[str] = Field(
        default=None,
        description="指定记忆引擎 (memobase/mem0/cognee)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "query": "咖啡偏好",
                "memory_type": "preference",
                "limit": 10
            }
        }


class MemoryUpdate(BaseModel):
    """更新记忆请求"""
    
    content: Optional[str] = Field(
        default=None,
        description="新的记忆内容"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="新的元数据"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "用户现在喜欢喝美式咖啡",
                "metadata": {"updated_reason": "user_correction"}
            }
        }


# ==================== 响应模型 ====================

class Memory(BaseModel):
    """记忆对象"""
    
    id: str = Field(..., description="记忆 ID")
    user_id: str = Field(..., description="用户 ID")
    content: str = Field(..., description="记忆内容")
    memory_type: MemoryType = Field(..., description="记忆类型")
    source: MemorySource = Field(..., description="记忆来源")
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="置信度"
    )
    
    class Config:
        from_attributes = True


class MemoryResponse(BaseModel):
    """记忆操作响应"""
    
    success: bool = Field(..., description="是否成功")
    data: Optional[Memory] = Field(default=None, description="记忆数据")
    message: str = Field(default="", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "id": "mem_123",
                    "user_id": "user_123",
                    "content": "用户喜欢喝拿铁咖啡",
                    "memory_type": "preference",
                    "source": "memobase",
                    "created_at": "2026-04-06T10:00:00Z"
                },
                "message": "记忆创建成功"
            }
        }


class MemoryListResponse(BaseModel):
    """记忆列表响应"""
    
    success: bool = Field(..., description="是否成功")
    data: List[Memory] = Field(default=[], description="记忆列表")
    total: int = Field(default=0, description="总数")
    limit: int = Field(default=10, description="限制数量")
    message: str = Field(default="", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "id": "mem_123",
                        "user_id": "user_123",
                        "content": "用户喜欢喝拿铁咖啡",
                        "memory_type": "preference",
                        "source": "memobase",
                        "created_at": "2026-04-06T10:00:00Z"
                    }
                ],
                "total": 1,
                "limit": 10,
                "message": "查询成功"
            }
        }


class EngineInfo(BaseModel):
    """记忆引擎信息"""
    
    name: str = Field(..., description="引擎名称")
    enabled: bool = Field(..., description="是否启用")
    status: str = Field(..., description="状态 (healthy/degraded/down)")
    latency_ms: Optional[float] = Field(default=None, description="延迟 (毫秒)")
    error_rate: Optional[float] = Field(default=None, description="错误率")


class HealthResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(..., description="整体状态")
    version: str = Field(..., description="应用版本")
    environment: str = Field(..., description="环境")
    timestamp: datetime = Field(..., description="检查时间")
    engines: Dict[str, EngineInfo] = Field(default={}, description="引擎状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "environment": "development",
                "timestamp": "2026-04-06T10:00:00Z",
                "engines": {
                    "memobase": {
                        "name": "Memobase",
                        "enabled": True,
                        "status": "healthy",
                        "latency_ms": 50.0
                    }
                }
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    
    success: bool = Field(default=False)
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "ValidationError",
                "message": "用户 ID 不能为空",
                "details": {"field": "user_id"}
            }
        }
