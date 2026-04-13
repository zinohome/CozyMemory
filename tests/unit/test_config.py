"""配置管理测试"""

import os
import pytest
from cozymemory.config import Settings


def test_settings_defaults():
    """默认配置值正确"""
    s = Settings()
    assert s.APP_NAME == "CozyMemory"
    assert s.APP_VERSION == "2.0.0"
    assert s.APP_ENV == "development"
    assert s.DEBUG is True
    assert s.PORT == 8000
    assert s.GRPC_PORT == 50051


def test_settings_mem0_defaults():
    """Mem0 引擎默认配置"""
    s = Settings()
    assert s.MEM0_API_URL == "http://localhost:8888"
    assert s.MEM0_TIMEOUT == 30.0
    assert s.MEM0_ENABLED is True


def test_settings_memobase_defaults():
    """Memobase 引擎默认配置"""
    s = Settings()
    assert s.MEMOBASE_API_URL == "http://localhost:8019"
    assert s.MEMOBASE_API_KEY == "secret"
    assert s.MEMOBASE_TIMEOUT == 60.0
    assert s.MEMOBASE_ENABLED is True


def test_settings_cognee_defaults():
    """Cognee 引擎默认配置"""
    s = Settings()
    assert s.COGNEE_API_URL == "http://localhost:8000"
    assert s.COGNEE_TIMEOUT == 300.0
    assert s.COGNEE_ENABLED is True


def test_settings_from_env(monkeypatch):
    """从环境变量读取配置"""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MEM0_API_URL", "http://mem0:8000")
    monkeypatch.setenv("MEM0_ENABLED", "false")
    s = Settings()
    assert s.APP_ENV == "production"
    assert s.MEM0_API_URL == "http://mem0:8000"
    assert s.MEM0_ENABLED is False


def test_settings_singleton():
    """全局 settings 实例可用"""
    from cozymemory.config import settings
    assert settings.APP_NAME == "CozyMemory"