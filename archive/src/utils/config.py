"""
配置管理模块

支持环境变量、.env 文件、默认值三层配置。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ==================== 应用配置 ====================
    APP_NAME: str = "CozyMemory"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = True
    
    # ==================== 服务配置 ====================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    
    # ==================== 数据库配置 ====================
    DATABASE_URL: str = "sqlite+aiosqlite:///./cozymemory.db"
    # PostgreSQL (生产环境):
    # DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/cozymemory"
    
    # ==================== Redis 配置 ====================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PREFIX: str = "cozymemory:"
    REDIS_ENABLED: bool = True  # 是否启用 Redis 缓存
    CACHE_TTL: int = 300  # 5 分钟
    
    # ==================== 缓存配置 ====================
    CACHE_MEMORY_MAX_SIZE: int = 1000  # 内存缓存最大条目数
    CACHE_NULL_TTL: int = 60  # 空值缓存 TTL (防穿透)
    CACHE_TTL_JITTER: float = 0.2  # TTL 抖动比例 (防雪崩)
    CACHE_HOT_THRESHOLD: int = 100  # 热点数据阈值 (访问次数)
    CACHE_HOT_TTL_MULTIPLIER: float = 2.0  # 热点数据 TTL 倍数
    
    # ==================== 记忆引擎配置 ====================
    # Memobase
    MEMOBASE_ENABLED: bool = True
    MEMOBASE_API_URL: str = "http://localhost:8001"
    MEMOBASE_API_KEY: Optional[str] = None
    
    # Mem0
    MEM0_ENABLED: bool = False
    MEM0_API_URL: str = "http://localhost:8002"
    MEM0_API_KEY: Optional[str] = None
    
    # Cognee
    COGNEE_ENABLED: bool = False
    COGNEE_API_URL: str = "http://localhost:8003"
    COGNEE_API_KEY: Optional[str] = None
    
    # ==================== 智能路由配置 ====================
    ROUTER_STRATEGY: str = "intent"  # intent, round_robin, weighted
    ROUTER_TIMEOUT: float = 5.0  # 秒
    FUSION_STRATEGY: str = "rrf"  # rrf (Reciprocal Rank Fusion), weighted
    
    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "json"  # json, text
    LOG_FILE: Optional[str] = "logs/cozymemory.log"
    
    # ==================== 监控配置 ====================
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # ==================== 安全配置 ====================
    API_KEY_HEADER: str = "X-API-Key"
    CORS_ORIGINS: list = ["*"]
    RATE_LIMIT: int = 100  # 每分钟请求数
    
    # ==================== 性能配置 ====================
    MAX_BATCH_SIZE: int = 100
    ASYNC_QUEUE_SIZE: int = 1000
    MAX_CONCURRENT_REQUESTS: int = 100


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 快捷访问
settings = get_settings()
