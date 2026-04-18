"""logging_config 单元测试

验证 configure_logging() 在 development/production 模式下的行为。
"""

import logging

import structlog

from cozymemory.logging_config import configure_logging


def test_configure_logging_development_sets_console_renderer():
    """development 模式使用 ConsoleRenderer"""
    configure_logging(env="development", level="INFO")
    config = structlog.get_config()
    # 最后一个处理器应是 ConsoleRenderer
    assert any(isinstance(p, structlog.dev.ConsoleRenderer) for p in config["processors"])


def test_configure_logging_production_sets_json_renderer():
    """production 模式使用 JSONRenderer"""
    configure_logging(env="production", level="INFO")
    config = structlog.get_config()
    assert any(isinstance(p, structlog.processors.JSONRenderer) for p in config["processors"])


def test_configure_logging_debug_level():
    """DEBUG 级别正确传递给 stdlib logging"""
    configure_logging(env="development", level="DEBUG")
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_warning_level():
    """WARNING 级别正确设置"""
    configure_logging(env="development", level="WARNING")
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_invalid_level_falls_back_to_info():
    """无效的级别名称 fallback 为 INFO"""
    configure_logging(env="development", level="INVALID")
    assert logging.getLogger().level == logging.INFO


def test_noisy_loggers_set_to_warning():
    """高频第三方库日志降噪为 WARNING"""
    configure_logging(env="development", level="DEBUG")
    for name in ("httpx", "httpcore", "grpc", "uvicorn.access"):
        assert logging.getLogger(name).level == logging.WARNING


def test_configure_logging_unknown_env_uses_console():
    """未知 env 值 fallback 为 ConsoleRenderer（else 分支）"""
    configure_logging(env="staging", level="INFO")
    config = structlog.get_config()
    assert any(isinstance(p, structlog.dev.ConsoleRenderer) for p in config["processors"])
