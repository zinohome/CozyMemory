"""
CozyMemory 适配器注册表
"""

from typing import Dict, Type

from .base import BaseAdapter
from .memobase import MemobaseAdapter
from .mem0 import Mem0Adapter

# 适配器注册表
ADAPTERS: Dict[str, Type[BaseAdapter]] = {
    "memobase": MemobaseAdapter,
    "mem0": Mem0Adapter,
    # "cognee": CogneeAdapter,  # TODO
}


def get_adapter(name: str, **kwargs) -> BaseAdapter:
    """获取适配器实例"""
    if name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {name}. Available: {list(ADAPTERS.keys())}")
    
    return ADAPTERS[name](**kwargs)


__all__ = ["BaseAdapter", "MemobaseAdapter", "Mem0Adapter", "ADAPTERS", "get_adapter"]
