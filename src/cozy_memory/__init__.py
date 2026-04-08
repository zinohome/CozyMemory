"""
CozyMemory - 统一记忆管理系统

整合 Memobase/Mem0/Cognee，提供统一 API 和智能路由。
"""

from .core import CozyMemory
from .models import Memory, MemoryCreate, MemoryQuery, MemoryType
from .adapters import BaseAdapter, MemobaseAdapter, Mem0Adapter

__version__ = "0.2.0"
__author__ = "蟹小五"

__all__ = [
    "CozyMemory",
    "Memory",
    "MemoryCreate",
    "MemoryQuery",
    "MemoryType",
    "BaseAdapter",
    "MemobaseAdapter",
    "Mem0Adapter",
]
