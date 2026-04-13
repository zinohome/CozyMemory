"""
Pytest 配置文件

配置 pytest 插件、fixtures、标记等。
"""

import pytest
import asyncio
from pathlib import Path
import sys

# 添加 src 到路径
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))


# 配置 pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
